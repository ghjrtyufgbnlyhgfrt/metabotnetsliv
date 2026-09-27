from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import qrcode
import time

# === API / session ===
# It's highly recommended to load these from environment variables or a config file
# for security reasons, rather than hardcoding them directly.
API_ID = 25874957
API_HASH = 'c89ef6fd9ba5c8a479abb1f4d2de248d'
SESSION_NAME = 'session'

async def main():
    """
    Main function to connect to Telegram, handle authentication (including QR login with 2FA),
    and send a confirmation message.
    """
    # Initialize the TelegramClient without proxy settings
    client = TelegramClient(
        SESSION_NAME,
        API_ID,
        API_HASH
    )

    try:
        await client.connect()

        if await client.is_user_authorized():
            print("✅ Already authorized!")
        else:
            print("📱 Logging in via QR code (with 2FA support)\n")

            while True:
                try:
                    # Initiate QR login
                    qr_login = await client.qr_login()

                    # Generate and display QR code
                    qr = qrcode.QRCode(version=1, box_size=3, border=2)
                    qr.add_data(qr_login.url)
                    qr.make(fit=True)

                    print("\033c", end="")  # Clear screen
                    print("🔄 New QR code generated\n")
                    print("Scan in Telegram → Settings → Devices → Connect Device\n")

                    qr.print_ascii(invert=True)
                    print(f"Time: {time.strftime('%H:%M:%S')}")

                    # Wait for the QR code to be scanned and confirmed
                    await asyncio.wait_for(qr_login.wait(), timeout=60)
                    print("\n✅ QR code successfully scanned!")
                    break

                except asyncio.TimeoutError:
                    print("⏳ QR code expired → generating a new one...")
                    continue
                except Exception as e:
                    error_str = str(e)
                    if "PASSWORD_HASH_INVALID" in error_str or "password" in error_str.lower():
                        print("\n🔑 Two-step verification password required!")
                        password = input("Enter your 2FA password: ")
                        await client.sign_in(password=password)
                        print("✅ Password accepted!")
                        break
                    elif "TOKEN_EXPIRED" in error_str or "expired" in error_str.lower():
                        print("⏳ QR code expired → refreshing...")
                        continue
                    else:
                        print(f"❌ An error occurred: {e}")
                        await asyncio.sleep(2)
                        continue

        # === After successful login ===
        me = await client.get_me()
        print(f"\n👤 Successfully logged in!")
        print(f"   Name: {me.first_name}")
        print(f"   Username: @{me.username}" if me.username else "")

        # Send a confirmation message to yourself
        await client.send_message('me', '✅ Telethon client successfully started with 2FA!')

        print("\n🚀 Client is running. Press Ctrl+C to stop.")
        await client.run_until_disconnected()

    except Exception as e:
        print(f"❌ An unexpected error occurred during client operation: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()
            print("Disconnected from Telegram.")

if __name__ == '__main__':
    # Ensure event loop policy is set for Windows compatibility if needed
    # (though asyncio.run generally handles this well in modern Python)
    # if sys.platform == "win32":
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

