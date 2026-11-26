"""CareFlow AI — Real-time Voice Agent Pipeline.
Coordinates Pipecat, ElevenLabs STT, Gemini LLM, ElevenLabs TTS, Function Tools, and Browser WebSocket Audio.
"""
import asyncio
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

_voice_dir = str(Path(__file__).parent.resolve())
if _voice_dir not in sys.path:
    sys.path.insert(0, _voice_dir)

from config import VoiceConfig
from prompts import CAREFLOW_VOICE_SYSTEM_PROMPT, CAREFLOW_INITIAL_GREETING
from tools import (
    ALL_VOICE_TOOLS,
    execute_check_availability,
    execute_book_appointment,
    execute_cancel_appointment,
)
from backend.app.schemas.common import normalize_phone_number, mask_phone_number

# Pipecat imports
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.pipeline.runner import PipelineRunner
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams
)
from pipecat.processors.aggregators.llm_response import LLMFullResponseAggregator
from pipecat.frames.frames import (
    Frame,
    TextFrame,
    TranscriptionFrame,
    OutputAudioRawFrame,
    LLMContextFrame,
    EndFrame
)
from pipecat.services.elevenlabs.stt import ElevenLabsSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.google.llm import GoogleLLMService

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CareFlowVoiceSession:
    """Manages an active real-time voice call session over WebSocket."""

    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.is_connected = False
        self.is_muted = False

        # Conversational dialogue state
        self.confirmed_phone: Optional[str] = None
        self.pending_phone: Optional[str] = None
        self.pending_intent: Optional[str] = None  # 'book' or 'cancel'
        self.selected_doctor: Optional[Dict[str, Any]] = None
        self.selected_slot: Optional[Dict[str, Any]] = None

        self.conversation_history: List[Dict[str, str]] = [
            {"role": "system", "content": CAREFLOW_VOICE_SYSTEM_PROMPT}
        ]

    async def send_event(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """Send a structured JSON event to the client matching NETWORK_PROTOCOL.md."""
        payload = {
            "type": event_type,
            "timestamp": _now_iso(),
            "data": data or {}
        }
        try:
            await self.websocket.send_text(json.dumps(payload))
        except Exception as e:
            logger.debug(f"Failed to send event {event_type} to client: {e}")

    async def send_audio_chunk(self, audio_bytes: bytes):
        """Stream synthesized audio bytes back to browser client."""
        try:
            await self.websocket.send_bytes(audio_bytes)
        except Exception as e:
            logger.debug(f"Failed to send audio bytes: {e}")

    async def on_user_transcript(self, text: str):
        """Invoked when user speech is transcribed."""
        if not text or not text.strip():
            return
        clean_text = text.strip()
        logger.info(f"[{self.session_id}] User said: {clean_text}")
        await self.send_event("transcript.user", {"text": clean_text})
        self.conversation_history.append({"role": "user", "content": clean_text})

    async def on_agent_transcript(self, text: str):
        """Invoked when agent response text is generated."""
        if not text or not text.strip():
            return
        clean_text = text.strip()
        logger.info(f"[{self.session_id}] Agent reply: {clean_text}")
        await self.send_event("transcript.agent", {"text": clean_text})
        self.conversation_history.append({"role": "assistant", "content": clean_text})

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with realtime WebSocket events and safety checks."""
        await self.send_event("tool.started", {"tool": tool_name, "params": arguments})

        result = {}
        if tool_name == "check_doctor_availability":
            result = execute_check_availability(
                doctor_id=arguments.get("doctor_id"),
                speciality=arguments.get("speciality"),
                date=arguments.get("date")
            )
        elif tool_name == "book_appointment":
            phone = arguments.get("phone_number", "")
            is_confirmed = False
            if self.confirmed_phone and phone:
                try:
                    is_confirmed = (normalize_phone_number(phone) == normalize_phone_number(self.confirmed_phone))
                except Exception:
                    is_confirmed = False

            result = execute_book_appointment(
                phone_number=phone,
                doctor_id=arguments.get("doctor_id", ""),
                slot_id=arguments.get("slot_id", ""),
                phone_confirmed=is_confirmed
            )
            if result.get("success"):
                await self.send_event("appointment.created", result)
        elif tool_name == "cancel_appointment":
            phone = arguments.get("phone_number", "")
            is_confirmed = False
            if self.confirmed_phone and phone:
                try:
                    is_confirmed = (normalize_phone_number(phone) == normalize_phone_number(self.confirmed_phone))
                except Exception:
                    is_confirmed = False

            result = execute_cancel_appointment(
                phone_number=phone,
                appointment_id=arguments.get("appointment_id"),
                phone_confirmed=is_confirmed
            )
            if result.get("success"):
                await self.send_event("appointment.cancelled", result)
        else:
            result = {
                "success": False,
                "error": {
                    "code": "UNKNOWN_TOOL",
                    "message": f"Tool '{tool_name}' is not recognized."
                }
            }

        await self.send_event("tool.completed", {"tool": tool_name, "result": result})
        return result


class CareFlowVoiceAgent:
    """Pipeline coordinator for Pipecat and voice services."""

    def __init__(self):
        self.config = VoiceConfig()
        self.vad_analyzer = None
        if getattr(self.config, "ENABLE_SILERO_VAD", True):
            try:
                from pipecat.audio.vad.silero import SileroVADAnalyzer
                self.vad_analyzer = SileroVADAnalyzer()
                logger.info("Silero VAD initialized successfully.")
            except Exception as e:
                logger.warning(f"Silero VAD initialization deferred: {e}")

    def build_pipecat_pipeline(
        self,
        websocket: WebSocket,
        session: CareFlowVoiceSession
    ) -> tuple[PipelineTask, PipelineRunner]:
        """Construct a real-time Pipecat pipeline with ElevenLabs STT/TTS and Gemini."""
        ws_params = FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=True
        )
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=ws_params
        )

        # 1. ElevenLabs STT
        stt = ElevenLabsSTTService(
            api_key=self.config.ELEVENLABS_API_KEY
        )

        # 2. Gemini LLM
        llm = GoogleLLMService(
            api_key=self.config.GEMINI_API_KEY,
            model=self.config.GEMINI_MODEL
        )

        # Register functions with Gemini
        async def on_check_availability(params):
            args = params.arguments if hasattr(params, "arguments") else {}
            return await session.execute_tool("check_doctor_availability", args)

        async def on_book_appointment(params):
            args = params.arguments if hasattr(params, "arguments") else {}
            return await session.execute_tool("book_appointment", args)

        async def on_cancel_appointment(params):
            args = params.arguments if hasattr(params, "arguments") else {}
            return await session.execute_tool("cancel_appointment", args)

        llm.register_function("check_doctor_availability", on_check_availability)
        llm.register_function("book_appointment", on_book_appointment)
        llm.register_function("cancel_appointment", on_cancel_appointment)

        # 3. ElevenLabs TTS
        tts = ElevenLabsTTSService(
            api_key=self.config.ELEVENLABS_API_KEY,
            voice_id=self.config.ELEVENLABS_VOICE_ID,
            model=self.config.ELEVENLABS_MODEL_ID
        )

        # Build pipeline stages
        pipeline = Pipeline([
            transport.input(),
            stt,
            llm,
            tts,
            transport.output()
        ])

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True
            )
        )

        runner = PipelineRunner()
        return task, runner

    async def run_session(self, websocket: WebSocket, session_id: str):
        """Run an active voice session until disconnect."""
        await websocket.accept()
        session = CareFlowVoiceSession(websocket, session_id)
        session.is_connected = True

        logger.info(f"Voice session {session_id} connected.")
        await session.send_event("call.started", {"session_id": session_id})
        await session.send_event("call.connected", {"session_id": session_id})

        # Send initial agent greeting
        await session.on_agent_transcript(CAREFLOW_INITIAL_GREETING)

        try:
            use_live_pipeline = self.config.is_fully_configured()

            if use_live_pipeline:
                logger.info("Starting live Pipecat voice pipeline with ElevenLabs & Gemini.")
                try:
                    task, runner = self.build_pipecat_pipeline(websocket, session)
                    await runner.run(task)
                    return
                except Exception as e:
                    logger.warning(f"Pipecat pipeline error, falling back to message receiver: {e}")

            # Robust message loop handling both binary audio chunks and JSON text messages
            while True:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break

                text_data = message.get("text")
                if text_data:
                    try:
                        event = json.loads(text_data)
                        ev_type = event.get("type")
                        if ev_type == "call.end":
                            logger.info(f"Session {session_id} ended by client.")
                            break
                        elif ev_type == "client.mute":
                            session.is_muted = bool(event.get("muted", False))
                            logger.info(f"Session {session_id} mute state: {session.is_muted}")
                        elif ev_type == "transcript.user" or ev_type == "text.input":
                            user_text = event.get("data", {}).get("text") or event.get("text", "")
                            if user_text:
                                await session.on_user_transcript(user_text)
                                reply = await self._handle_conversational_turn(user_text, session)
                                await session.on_agent_transcript(reply)
                    except json.JSONDecodeError:
                        pass

                bytes_data = message.get("bytes")
                if bytes_data and not session.is_muted:
                    if self.vad_analyzer:
                        try:
                            # Evaluate voice activity using Silero VAD
                            conf = self.vad_analyzer.voice_confidence(bytes_data)
                            if conf > 0.5:
                                logger.debug(f"Silero VAD speech detected (confidence: {conf:.2f})")
                        except Exception:
                            pass

        except WebSocketDisconnect:
            logger.info(f"Voice session {session_id} disconnected by client.")
        except Exception as e:
            logger.error(f"Voice session {session_id} exception: {e}")
            await session.send_event("error", {"message": str(e)})
        finally:
            session.is_connected = False
            await session.send_event("call.ended", {"session_id": session_id})
            logger.info(f"Voice session {session_id} closed.")

    async def _handle_conversational_turn(self, user_text: str, session: CareFlowVoiceSession) -> str:
        """Intelligent conversational state handler with real database tool execution."""
        text = user_text.lower().strip()

        # 1. Verbal Confirmation Handling (Evaluated first if a phone confirmation is pending)
        if session.pending_phone and any(w in text for w in ["yes", "correct", "that's right", "sure", "yep", "yeah", "confirm", "please cancel"]):
            session.confirmed_phone = session.pending_phone

            # Handle cancellation confirmation
            if session.pending_intent == "cancel":
                tool_result = await session.execute_tool("cancel_appointment", {
                    "phone_number": session.confirmed_phone
                })
                session.pending_intent = None
                session.pending_phone = None
                session.confirmed_phone = None
                if tool_result.get("success"):
                    return "Your appointment has been cancelled successfully. Is there anything else I can help you with?"
                else:
                    err_msg = tool_result.get("error", {}).get("message", "No active appointment was found.")
                    return f"{err_msg} Would you like to check another number?"

            # Handle booking confirmation
            if session.selected_doctor and session.selected_slot:
                tool_result = await session.execute_tool("book_appointment", {
                    "phone_number": session.confirmed_phone,
                    "doctor_id": session.selected_doctor["id"],
                    "slot_id": session.selected_slot["id"]
                })
                session.pending_phone = None
                session.confirmed_phone = None
                if tool_result.get("success"):
                    doc_name = session.selected_doctor.get("name", "Doctor")
                    slot_time = session.selected_slot.get("time", "your selected time")
                    slot_date = session.selected_slot.get("date", "tomorrow")
                    session.selected_slot = None
                    return f"Your appointment with {doc_name} is confirmed for {slot_date} at {slot_time}. Thank you for choosing CareFlow!"
                else:
                    err_msg = tool_result.get("error", {}).get("message", "Slot is no longer available.")
                    return f"I apologize, {err_msg} Would you like to choose another time?"

        # 2. Verbal Confirmation Rejection (User says number is wrong)
        if session.pending_phone and any(w in text for w in ["no", "incorrect", "wrong", "not right", "nope", "that's wrong"]):
            session.pending_phone = None
            session.confirmed_phone = None
            return "My apologies. Could you please provide your 10-digit phone number again?"

        # 3. Cancellation flow: User asks to cancel an appointment
        if any(w in text for w in ["cancel", "cancellation"]):
            session.pending_intent = "cancel"
            session.confirmed_phone = None
            session.pending_phone = None
            return "I can help you cancel your appointment. What is the 10-digit phone number you used for booking?"

        # 3. Extract digits if caller spoke a phone number
        raw_digits = re.sub(r"\D", "", text)
        if len(raw_digits) >= 7:
            session.pending_phone = raw_digits
            session.confirmed_phone = None
            spaced_digits = ", ".join(" ".join(raw_digits[i:i+3]) for i in range(0, len(raw_digits), 3))
            return f"I have your phone number as {spaced_digits}. Can you confirm this is correct?"

        # 4. Availability lookup: Caller asks about doctors, specialities, or availability
        if any(w in text for w in ["doctor", "cardiologist", "cardiology", "dermatologist", "dermatology", "pediatrician", "available", "availability", "slot", "appointment"]):
            speciality = None
            if "cardio" in text:
                speciality = "Cardiology"
            elif "derma" in text:
                speciality = "Dermatology"
            elif "pediatric" in text:
                speciality = "Pediatrics"

            # Execute real availability tool
            tool_result = await session.execute_tool("check_doctor_availability", {
                "speciality": speciality
            })

            availability = tool_result.get("availability", [])
            if not availability:
                return "I checked our schedule, but no slots are available matching that request. Would you like to check another speciality or date?"

            # Present the first available doctor and up to 2 slots
            first_doc = availability[0]
            session.selected_doctor = {
                "id": first_doc["doctor_id"],
                "name": first_doc["doctor_name"],
                "speciality": first_doc["speciality"]
            }
            slots = first_doc.get("slots", [])
            if slots:
                session.selected_slot = {
                    "id": slots[0]["id"],
                    "time": slots[0]["time"],
                    "date": first_doc["date"]
                }
                slot_times = ", ".join(s["time"] for s in slots[:2])
                return f"We have {first_doc['doctor_name']} in {first_doc['speciality']} available on {first_doc['date']} at {slot_times}. Would you like the {slots[0]['time']} slot?"

        # 5. Selecting a slot time (e.g. "10:30", "10:30 am", "morning", "first one")
        if (session.selected_doctor and session.selected_slot) and not session.pending_phone:
            return "Great. To book this appointment, may I please have your 10-digit phone number?"

        # 6. Greetings
        if any(w in text for w in ["hello", "hi", "hey"]):
            return "Hello! How can I assist you with your doctor appointments today?"

        return "I can help you check doctor availability, book an appointment, or cancel one. How can I assist you?"
