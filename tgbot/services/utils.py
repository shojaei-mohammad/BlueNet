import asyncio
import logging
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from io import BytesIO

import jdatetime
import qrcode
from PIL import Image
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from qrcode.main import QRCode


def convert_english_digits_to_farsi(input_number: str | Decimal | int | float) -> str:
    """
    Convert English digits in a string to their Farsi equivalents.

    Parameters:
    - input_string (str): A string that potentially contains English digits.

    Returns:
    - str: The input string with English digits replaced by their Farsi equivalents.

    Note:
    If an error occurs during the conversion, a log entry is made and the original string is returned.
    """

    farsi_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"

    try:
        if isinstance(input_number, (Decimal, int, float)):
            input_number = str(input_number)
        digit_translation = str.maketrans(english_digits, farsi_digits)
        return input_number.translate(digit_translation)
    except Exception as e:
        logging.info(f"Error converting to Farsi: {e}")
        return input_number


def format_currency(
    amount: int | float | Decimal,
    convert_to_farsi: bool = False,
) -> str:
    try:
        # Check if the amount is a valid number
        if not isinstance(amount, (int, float, Decimal)):
            raise ValueError(
                f"Invalid amount type: {type(amount)}. Expected an integer or float."
            )

        # Format the number with comma as thousands separator and specified decimal places
        if isinstance(amount, int):
            formatted_amount = f"{amount:,}"
        else:
            formatted_amount = f"{int(amount):,}"

        logging.info(f"Formatted amount: {formatted_amount}")

        if convert_to_farsi:
            formatted_amount = convert_english_digits_to_farsi(formatted_amount)
            logging.info(f"Converted to Farsi digits: {formatted_amount}")

        return formatted_amount
    except Exception as e:
        logging.error(f"Error formatting currency: {e}")
        return "N/A"


def convert_to_shamsi(greg_date: datetime) -> str:
    """
    Convert a Gregorian datetime object to Shamsi (Jalali) date.

    Args:
        greg_date (datetime): The datetime object representing a Gregorian date.

    Returns:
        str: Shamsi date in the format "YYYY/MM/DD" or "YYYY/MM/DD HH:MM",
             with digits converted to Farsi. Time is included only if present in the input.

    Raises:
        ValueError: If there's an error related to the datetime object.
    """
    try:
        # Convert Gregorian date to Shamsi date
        shamsi_date = jdatetime.datetime.fromgregorian(datetime=greg_date)
        # Format the Shamsi date with or without time based on input
        if isinstance(greg_date, date):
            shamsi_date_str = shamsi_date.strftime("%Y/%-m/%-d")
        else:
            shamsi_date_str = shamsi_date.strftime("%Y/%-m/%-d %H:%M")

    except ValueError as e:
        logging.error(
            "An error occurred during the conversion to Shamsi, Error: {0}".format(e)
        )
        return "Invalid Date"

    return convert_english_digits_to_farsi(shamsi_date_str)


def convert_days_to_epoch(days, platform: str):
    """
    Calculates the epoch value representing the expiry date set a specific number of days after first use.

    The calculation is based on a predefined relationship where each day corresponds to a fixed negative value.
    This negative value is used as a special code to signify the number of days after first use for expiry.
    The function multiplies the number of days by this fixed negative value to calculate the epoch value.

    Parameters:
    - days (int): The number of days after first use for the expiry.

    Returns:
    - int: The calculated epoch value for the expiry date.

    Example:
    >>> convert_days_to_epoch(10)
    # Returns -864000000 for an expiry 10 days after first use.
    """
    if platform == "xui":

        value_per_day = -86400000
        return value_per_day * days
    else:
        # Get the current date-time
        current_dt = datetime.now(timezone.utc)

        # Add the days to get the future date-time
        future_dt = current_dt + timedelta(days=days)

        # Convert to epoch time in milliseconds
        epoch = int(future_dt.timestamp() * 1000)
        return epoch


def gb_to_bytes(gb):
    # 1 GB is 1024^3 bytes
    return int(gb * (1024**3))


# async def generate_qr_code(data: str) -> str:
#     """
#     Generate a custom QR code using the QRCODE-MONKEY API.
#
#     This function takes in data to be encoded in the QR code, the path to a logo which
#     is overlayed on the QR code, and the path to save the generated QR code image.
#
#     :param data: The content to be encoded in the QR code.
#     :return: True if QR code generation and saving was successful, None otherwise.
#     """
#
#     url = "https://api.qrcode-monkey.com/qr/custom"
#
#     try:
#
#         payload = {
#             "config": {
#                 "body": "circular",
#                 "eye": "frame2",
#                 "eyeBall": "ball14",
#                 "erf1": ["fv"],
#                 "erf2": [],
#                 "erf3": [],
#                 "brf1": [],
#                 "brf2": [],
#                 "brf3": [],
#                 "bodyColor": "#010536",
#                 "bgColor": "#FFFFFF",
#                 "eye1Color": "#D52B4B",
#                 "eye2Color": "#D52B4B",
#                 "eye3Color": "#D52B4B",
#                 "eyeBall1Color": "#010536",
#                 "eyeBall2Color": "#010536",
#                 "eyeBall3Color": "#010536",
#                 "gradientColor1": "010536",
#                 "gradientColor2": "010536",
#                 "gradientType": "radial",
#                 "gradientOnEyes": False,
#             },
#             "size": 300,
#             "download": "imageUrl",
#             "file": "png",
#             "data": data,
#         }
#
#         headers = {"cache-control": "no-cache", "content-type": "application/json"}
#
#         async with aiohttp.ClientSession() as session:
#             async with session.post(url, json=payload, headers=headers) as response:
#                 if response.status == 200:
#                     json_response = await response.json()
#                     qr_url = json_response["imageUrl"]
#
#                     if not qr_url.startswith("http"):
#                         qr_url = "https:" + qr_url
#
#                     return qr_url
#                 else:
#                     text = await response.text()
#                     logging.error(
#                         f"Error generating QR code: {response.status}, {text}"
#                     )
#     except Exception as e:
#         logging.error(f"An error occurred during generating qrcode {e}")
#         raise


async def generate_qr_code(data: str, size: int = 300) -> bytes:
    """
    Generate a QR code from input string and return as bytes.

    Args:
        data (str): The string data to encode in QR code
        size (int): The size of the output image in pixels (default: 300)

    Returns:
        bytes: PNG image data as bytes

    Raises:
        ValueError: If data is empty or None
        Exception: If QR code generation fails
    """
    if not data or not data.strip():
        raise ValueError("Input data cannot be empty")

    try:
        # Create QR code instance
        qr = QRCode(
            version=1,  # Controls the size of the QR Code (1 is 21x21)
            error_correction=qrcode.constants.ERROR_CORRECT_M,  # Medium error correction (~15%)
            box_size=10,  # Size of each box in pixels
            border=1,  # Border size in boxes
        )

        # Add data and make the QR code
        qr.add_data(data)
        qr.make(fit=True)

        # Create image
        qr_image = qr.make_image(fill_color="black", back_color="white")

        # Resize to specified size while maintaining aspect ratio
        qr_image = qr_image.resize((size, size), Image.Resampling.LANCZOS)

        # Convert to bytes
        img_buffer = BytesIO()
        qr_image.save(img_buffer, format="PNG", optimize=True)
        img_buffer.seek(0)

        return img_buffer.getvalue()

    except Exception as e:
        raise Exception(f"Failed to generate QR code: {str(e)}")


# async def upload_image(
#     url: str = "https://api.qrcode-monkey.com/qr/uploadImage",
# ) -> str | None:
#     logo_path = Path(__file__).parents[2] / "static/logo.png"
#
#     if not logo_path.exists():
#         logging.error(f"Logo image file does not exist: {logo_path}")
#         return None
#
#     # Create a custom SSL context that doesn't verify the certificate
#     ssl_context = ssl.create_default_context()
#     ssl_context.check_hostname = False
#     ssl_context.verify_mode = ssl.CERT_NONE
#
#     conn = aiohttp.TCPConnector(ssl=ssl_context)
#
#     async with aiohttp.ClientSession(connector=conn) as session:
#         try:
#             data = aiohttp.FormData()
#             async with aioopen(logo_path, "rb") as image_file:
#                 file_content = await image_file.read()
#                 data.add_field("file", file_content, filename=logo_path.name)
#
#             logging.info(f"Attempting to upload image to {url}")
#             async with session.post(url, data=data, timeout=30) as response:
#                 response.raise_for_status()
#                 json_response = await response.json(content_type=None)
#                 logging.info("Image uploaded successfully")
#                 return json_response["file"]
#         except aiohttp.ClientConnectorError as e:
#             logging.error(f"Connection error: {str(e)}")
#         except aiohttp.ClientResponseError as e:
#             logging.error(f"Error uploading image: {e.status}, {e.message}")
#         except aiohttp.ClientError as e:
#             logging.error(f"Client error: {str(e)}")
#         except asyncio.TimeoutError:
#             logging.error("Request timed out")
#         except KeyError:
#             logging.error("Unexpected response format: 'file' key not found")
#         except Exception as e:
#             logging.error(f"Unexpected error: {str(e)}", exc_info=True)
#
#     return None


# Telegram limits
MESSAGES_PER_SECOND = 30
MESSAGES_PER_MINUTE = 20 * 60  # 20 messages per minute per chat


async def send_message_with_rate_limit(
    bot: Bot,
    chat_id: int,
    text: str,
    markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None,
):
    try:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
        return True
    except TelegramAPIError as e:
        logging.error(f"Failed to send message to {chat_id}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error when sending message to {chat_id}: {e}")
        return False


async def broadcast_messages(
    bot: Bot,
    chat_ids: list,
    message: str,
    markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None,
):
    successful = 0
    failed = 0
    start_time = asyncio.get_event_loop().time()

    try:
        for i, chat_id in enumerate(chat_ids):
            if i % MESSAGES_PER_SECOND == 0 and i != 0:
                await asyncio.sleep(1)  # Sleep for 1 second every 30 messages

            if i % MESSAGES_PER_MINUTE == 0 and i != 0:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed < 60:
                    await asyncio.sleep(60 - elapsed)
                start_time = asyncio.get_event_loop().time()

            success = await send_message_with_rate_limit(bot, chat_id, message, markup)
            if success:
                successful += 1
            else:
                failed += 1

            if (i + 1) % 100 == 0:
                logging.info(
                    f"Broadcast progress: {i + 1}/{len(chat_ids)} messages sent"
                )

    except Exception as e:
        logging.error(f"Error during broadcast: {e}")

    logging.info(f"Broadcast completed. Successful: {successful}, Failed: {failed}")
    return successful, failed
