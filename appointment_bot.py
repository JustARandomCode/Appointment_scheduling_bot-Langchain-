from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
load_dotenv()


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedAppointmentAgent:
    def __init__(self, gemini_api_key: str, google_sheets_credentials_path: Optional[str] = None, sheet_url: Optional[str] = None):
        """Initialize the optimized appointment scheduling agent"""

        # Initialize Gemini LLM
        try:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                google_api_key=gemini_api_key,
                temperature=0.1,
                convert_system_message_to_human=True
            )

            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-pro')
            logger.info("✅ Gemini AI initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini AI: {e}")
            raise

        # Initialize Google Sheets (optional)
        self.gc = None
        self.sheet_url = sheet_url
        if google_sheets_credentials_path and sheet_url:
            self.gc = self._setup_google_sheets(google_sheets_credentials_path)

        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            k=5
        )

        # Store appointment data
        self.appointments_cache = []

        # Simplified state - let LLM manage complexity
        self.appointment_data = {}

        # Initialize tools and agent
        self.tools = self._create_tools()
        self.agent = self._create_agent()

    def _setup_google_sheets(self, credentials_path: str) -> Optional[gspread.Client]:
        """Setup Google Sheets connection"""
        try:
            if not os.path.exists(credentials_path):
                logger.warning(f"⚠️ Google Sheets credentials file not found: {credentials_path}")
                return None

            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                credentials_path, scope
            )
            client = gspread.authorize(creds)
            logger.info("✅ Google Sheets initialized successfully")
            return client

        except Exception as e:
            logger.warning(f"⚠️ Google Sheets setup failed: {e}")
            return None

    def _append_to_google_sheets(self, data: dict):
        """Append appointment data to Google Sheets"""
        try:
            if self.gc and self.sheet_url:
                sh = self.gc.open_by_url(self.sheet_url)
                worksheet = sh.sheet1

                worksheet.append_row([
                    data.get('name', ''),
                    data.get('appointment_type', ''),
                    data.get('date', ''),
                    data.get('time', ''),
                    data.get('email', ''),
                    data.get('phone', ''),
                    data.get('created_at', ''),
                    data.get('status', '')
                ])
                logger.info("✅ Appointment appended to Google Sheets.")
            else:
                logger.warning("⚠️ Google Sheets client not configured. Skipping append.")
        except Exception as e:
            logger.error(f"❌ Failed to append to Google Sheets: {e}")

    def _create_tools(self):
        """Create tools for appointment management - Keep only essential Python operations"""

        def check_availability(date_time: str) -> str:
            """Check if the requested time slot is available"""
            try:
                # Simple availability check against existing appointments
                for appointment in self.appointments_cache:
                    if (appointment.get('date') in date_time and
                        appointment.get('time') in date_time):
                        return f"❌ Time slot {date_time} is already booked. Please choose another time."

                return f"✅ Time slot {date_time} is available!"

            except Exception as e:
                logger.error(f"Error checking availability: {e}")
                return f"✅ Time slot appears available"

        def save_appointment(appointment_json: str) -> str:
            """Save complete appointment data as JSON string with fields: name, appointment_type, date, time, email, phone"""
            try:
                data = json.loads(appointment_json)

                # Validate required fields
                required_fields = ['name', 'appointment_type', 'date', 'time']
                missing_fields = [field for field in required_fields if not data.get(field)]

                if missing_fields:
                    return f"❌ Cannot save appointment. Missing: {', '.join(missing_fields)}"

                # Add metadata
                data['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data['status'] = 'Confirmed'

                # Save to cache
                self.appointments_cache.append(data)

                # Save to Google Sheets
                self._append_to_google_sheets(data)

                logger.info(f"✅ Appointment saved for {data.get('name')}")
                return f"✅ Appointment successfully saved for {data.get('name')}!"

            except Exception as e:
                logger.error(f"Error saving appointment: {e}")
                return f"⚠️ There was an issue saving the appointment: {str(e)}"

        def get_current_datetime() -> str:
            """Get current date and time for reference"""
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return [
            Tool(
                name="check_availability",
                description="Check if appointment time is available. Use format: 'YYYY-MM-DD HH:MM'",
                func=check_availability
            ),
            Tool(
                name="save_appointment",
                description="Save complete appointment data as JSON string with fields: name, appointment_type, date, time, email, phone",
                func=save_appointment
            ),
            Tool(
                name="get_current_datetime",
                description="Get current date and time for reference and calculations",
                func=get_current_datetime
            )
        ]

    def _create_agent(self):
        """Create the LangChain agent with comprehensive prompt"""

        prompt_template = PromptTemplate(
            input_variables=["input", "agent_scratchpad", "tools", "tool_names", "chat_history"],
            template="""You are a friendly, professional appointment scheduling assistant for a healthcare practice. Your role is to help users book appointments through natural conversation while gathering all necessary information.

## Your Personality:
- Warm, empathetic, and professional
- Patient and understanding
- Clear in communication
- Efficient but not rushed

## Conversation Flow:
1. **Greeting**: Warmly introduce yourself and ask how you can help
2. **Information Collection**: Gather user details conversationally
3. **Appointment Details**: Understand their needs and preferences
4. **Booking Process**: Guide them through scheduling
5. **Confirmation**: Confirm all details before finalizing

CORE RESPONSIBILITIES:
1. Extract and validate patient information from natural conversation
2. Guide patients through the appointment booking process
3. Handle date/time parsing and validation intelligently
4. Maintain a friendly, professional healthcare assistant persona
5. Ensure all required information is collected before booking

AVAILABLE TOOLS:
{tools}

TOOL NAMES: {tool_names}

CONVERSATION CONTEXT:
{chat_history}

INTELLIGENT INFORMATION EXTRACTION RULES:
- Extract names from phrases like "My name is...", "I'm...", "This is...", or standalone name inputs
- Parse dates flexibly: "tomorrow", "next Monday", "December 20th", "12/20/2024", relative terms
- Parse times flexibly: "2pm", "14:00", "2:30 PM", "afternoon", "morning"
- Identify appointment types: checkup, consultation, follow-up, urgent, specialist, dental, etc.
- Extract email addresses and phone numbers automatically from user input
- Handle confirmation responses: "yes", "correct", "looks good", "confirm"

CONVERSATION FLOW MANAGEMENT:
1. Greeting: Welcome patient warmly and ask for their name
2. Information Collection: Gather name, appointment type, preferred date/time, email, phone
3. Confirmation: Summarize all details and ask for confirmation
4. Booking: Use save_appointment tool with complete JSON data
5. Completion: Provide confirmation with all appointment details

RESPONSE GUIDELINES:
- Be conversational and natural, not robotic
- Ask for one piece of information at a time if missing
- Validate dates (not in the past, reasonable business hours)
- Always confirm details before saving
- Handle errors gracefully with helpful suggestions
- Use emojis appropriately for healthcare context: 🏥 👤 📅 🕐 📧 ✅ ❌

CRITICAL: Always use the tools when needed. For saving appointments, format data as JSON:
{{"name": "John Doe", "appointment_type": "checkup", "date": "2024-12-20", "time": "14:00", "email": "john@email.com", "phone": "1234567890"}}

Current user input: {input}

Think step by step:
1. What information do I have so far?
2. What information is still needed?
3. How should I respond to guide the conversation forward?
4. Do I need to use any tools?

{agent_scratchpad}"""
        )

        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt_template
        )

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True,
            return_intermediate_steps=False
        )

    def process_message(self, user_message: str) -> str:
        """Process user message using the LLM agent"""
        try:
            logger.info(f"Processing message: {user_message}")

            # Let the LLM agent handle everything
            response = self.agent.invoke({
                "input": user_message,
                "chat_history": self.memory.chat_memory.messages
            })

            return response.get("output", "I apologize, but I'm having trouble processing your request. Could you please try again?")

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "I apologize, but I encountered an error. Could you please repeat your request?"

    def reset_conversation(self):
        """Reset conversation state"""
        self.memory.clear()
        self.appointment_data = {}

# Flask app creation function
def create_appointment_bot(gemini_api_key: str, google_creds_path: Optional[str] = None, sheet_url: Optional[str] = None):
    """Create and configure the appointment bot Flask app"""

    try:
        agent = OptimizedAppointmentAgent(
            gemini_api_key=gemini_api_key,
            google_sheets_credentials_path=google_creds_path,
            sheet_url=sheet_url
        )
        logger.info("🤖 Optimized appointment agent initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize appointment agent: {e}")
        raise

    app = Flask(__name__)
    CORS(app, origins=["*"])

    @app.route('/webhook/chat', methods=['POST'])
    def chat_webhook():
        """Main webhook endpoint for chat messages"""
        try:
            data = request.get_json()
            if not data or 'message' not in data:
                return jsonify({'error': 'Missing message in request'}), 400

            message = data['message'].strip()
            if not message:
                return jsonify({'error': 'Empty message'}), 400

            response = agent.process_message(message)

            return jsonify({
                'response': response,
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            })

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return jsonify({
                'error': 'I apologize, but I\'m experiencing technical difficulties. Please try again.',
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }), 500

    @app.route('/test', methods=['POST'])
    def test_chat():
        """Test endpoint for direct message testing"""
        try:
            data = request.get_json()
            if not data or 'message' not in data:
                return jsonify({'error': 'Missing message in request'}), 400

            message = data['message'].strip()
            response = agent.process_message(message)

            return jsonify({
                'response': response,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Test endpoint error: {e}")
            return jsonify({
                'error': 'Service temporarily unavailable. Please try again.',
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        try:
            return jsonify({
                'status': 'healthy',
                'model': 'gemini-1.5-pro',
                'framework': 'langchain-optimized',
                'sheets_enabled': agent.gc is not None,
                'appointments_in_cache': len(agent.appointments_cache),
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/reset', methods=['POST'])
    def reset_conversation():
        """Reset conversation state"""
        try:
            agent.reset_conversation()

            return jsonify({
                'status': 'success',
                'message': 'Conversation reset successfully',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Reset error: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/', methods=['GET'])
    def home():
        """Home endpoint"""
        return jsonify({
            'message': 'Optimized Healthcare Appointment Bot API - LLM-Driven',
            'version': '5.0',
            'framework': 'langchain + gemini-1.5-pro',
            'optimization': 'Maximum LLM delegation',
            'status': 'running',
            'timestamp': datetime.now().isoformat()
        })

    return app

if __name__ == '__main__':


    gemini_api_key = os.getenv("GEMINI_API_KEY")

    google_creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    sheet_url = os.getenv("GOOGLE_SHEET_URL")

    
    flask_host = os.getenv("FLASK_HOST", "0.0.0.0") 
    flask_port = int(os.getenv("FLASK_PORT", 5000)) 
    flask_debug = os.getenv("FLASK_DEBUG", "True").lower() == "true" 

    if not gemini_api_key:
        logger.error("❌ GEMINI_API_KEY environment variable not set. Please check your .env file.")
        
        import sys
        sys.exit(1)

    
    app = create_appointment_bot(
        gemini_api_key=gemini_api_key,
        google_creds_path=google_creds_path,
        sheet_url=sheet_url
    )
    
    app.run(debug=flask_debug, host=flask_host, port=flask_port)