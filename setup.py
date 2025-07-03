

#Setup script for Gemini Appointment Scheduling Bot


import os
import sys
import subprocess

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Packages installed successfully!")
    except subprocess.CalledProcessError:
        print("❌ Failed to install packages. Please run: pip install -r requirements.txt")
        return False
    return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    print("\n🔧 Checking environment configuration...")
    
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create a .env file with the following variables:")
        print("- GEMINI_API_KEY")
        print("- GOOGLE_CREDENTIALS_PATH")
        print("- GOOGLE_SHEET_URL")
        return False
    
    # Read .env file and check for required variables
    required_vars = ['GEMINI_API_KEY', 'GOOGLE_CREDENTIALS_PATH', 'GOOGLE_SHEET_URL']
    with open('.env', 'r') as f:
        env_content = f.read()
    
    missing_vars = []
    for var in required_vars:
        if f"{var}=" not in env_content or f"{var}=your-" in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing or incomplete environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ Environment file looks good!")
    return True

def check_google_credentials():
    """Check if Google service account file exists"""
    print("\n🔑 Checking Google credentials...")
    
    # Try to read the credentials path from .env
    creds_path = None
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('GOOGLE_CREDENTIALS_PATH='):
                    creds_path = line.split('=', 1)[1].strip()
                    break
    
    if not creds_path or not os.path.exists(creds_path):
        print("❌ Google service account file not found!")
        print("Please:")
        print("1. Create a Google Cloud service account")
        print("2. Download the JSON credentials file")
        print("3. Save it as specified in GOOGLE_CREDENTIALS_PATH")
        return False
    
    print("✅ Google credentials file found!")
    return True

def main():
    """Main setup function"""
    print("🤖 Setting up Gemini Appointment Scheduling Bot...\n")
    
    success = True
    
    # Install requirements
    if not install_requirements():
        success = False
    
    # Check environment file
    if not check_env_file():
        success = False
    
    # Check Google credentials
    if not check_google_credentials():
        success = False
    
    print("\n" + "="*50)
    if success:
        print("🎉 Setup completed successfully!")
        print("\nTo run the bot:")
        print("python appointment_bot.py")
        print("\nEndpoints will be available at:")
        print("- http://localhost:5000/webhook/chat (main webhook)")
        print("- http://localhost:5000/test (testing)")
        print("- http://localhost:5000/health (health check)")
    else:
        print("❌ Setup incomplete. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()