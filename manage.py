#!/usr/bin/env python3
"""
Management tool for AI Support Agent.
Unified entry point for administrative tasks.
"""
import sys
import os
import argparse
import asyncio
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def cmd_migrate():
    """Asynchronous database migration."""
    logger.info("🔄 Syncing database schema...")
    from models import init_db
    try:
        await init_db()
        logger.info("✅ Database schema is up to date.")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")

def cmd_start():
    """Start the bot."""
    logger.info("🚀 Starting AI Support Agent...")
    try:
        # We use subprocess to ensure clean environment and signal handling
        subprocess.run([sys.executable, "bot.py"], check=True)
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped by user.")

def cmd_operators_add(operator_id: str):
    """Add an operator ID to .env."""
    env_path = ".env"
    if not os.path.exists(env_path):
        logger.error("❌ .env file not found. Run 'python manage.py env init' first.")
        return
        
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        found = False
        for line in lines:
            if line.startswith("OPERATOR_IDS="):
                current = line.split("=", 1)[1].strip()
                ids = [x.strip() for x in current.split(",") if x.strip()]
                if operator_id in ids:
                    logger.info(f"⚠️ Operator {operator_id} already exists.")
                    return
                ids.append(operator_id)
                new_lines.append(f"OPERATOR_IDS={','.join(ids)}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"OPERATOR_IDS={operator_id}\n")
            
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        logger.info(f"✅ Operator {operator_id} added.")
    except Exception as e:
        logger.error(f"❌ Error: {e}")

def cmd_env_init(force: bool):
    """Initialize .env file."""
    if os.path.exists(".env") and not force:
        logger.warning("⚠️ .env already exists. Use --force to overwrite.")
        return
        
    template = """# GigaChat API
GIGACHAT_CLIENT_ID=
GIGACHAT_CLIENT_SECRET=
GIGACHAT_AUTHORIZATION_KEY=
GIGACHAT_SCOPE=GIGACHAT_API_PERS

# Telegram Bot
TELEGRAM_BOT_TOKEN=

# Sber Salute Speech (Voice)
SALUTE_SPEECH_CLIENT_ID=
SALUTE_SPEECH_CLIENT_SECRET=

# Database & RAG
DATABASE_URL=sqlite+aiosqlite:///./support.db
CHROMA_DB_PATH=./chroma_db
EMBEDDING_MODEL_NAME=ai-sage/Giga-Embeddings-instruct
OPERATOR_IDS=

# O2O & Mini App
DG_API_KEY=
NGROK_AUTHTOKEN=
WEBAPP_URL=http://localhost:8000
"""
    with open(".env", "w", encoding="utf-8") as f:
        f.write(template)
    logger.info("✅ .env template created. Please fill in your API keys.")

def main():
    parser = argparse.ArgumentParser(description="AI Support Agent Manager")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("start", help="Start the bot")
    subparsers.add_parser("migrate", help="Initialize/Update database")
    
    op_p = subparsers.add_parser("operators", help="Manage operators")
    op_s = op_p.add_subparsers(dest="op_cmd")
    add_p = op_s.add_parser("add", help="Add operator")
    add_p.add_argument("id", help="Telegram User ID")
    
    env_p = subparsers.add_parser("env", help="Manage environment")
    env_s = env_p.add_subparsers(dest="env_cmd")
    init_p = env_s.add_parser("init", help="Create .env template")
    init_p.add_argument("--force", action="store_true")

    args = parser.parse_args()
    
    if args.command == "start":
        cmd_start()
    elif args.command == "migrate":
        asyncio.run(cmd_migrate())
    elif args.command == "operators" and args.op_cmd == "add":
        cmd_operators_add(args.id)
    elif args.command == "env" and args.env_cmd == "init":
        cmd_env_init(args.force)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
