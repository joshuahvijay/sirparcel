import streamlit as st
import pandas as pd
import time
import json
import os
from fpdf import FPDF
from datetime import datetime
import asyncio
import httpx
import base64

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Sir Parcel",
    page_icon="📦",
    layout="wide"
)

# --- STYLING ---
def get_base64_of_bin_file(bin_file):
    """Encodes a binary file to a base64 string."""
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# --- BACKGROUND IMAGE ---
# Make sure the image file is in the same directory as this script.
img_file = "f51f4e152830793.Y3JvcCwxNTM0LDEyMDAsMzQsMA.jpg"
if os.path.exists(img_file):
    bg_image_base64 = get_base64_of_bin_file(img_file)
    bg_image_style = f"background-image: url(data:image/jpg;base64,{bg_image_base64});"
else:
    # Fallback color if the image is not found
    st.warning(f"Background image '{img_file}' not found. Using fallback color.")
    bg_image_style = "background-color: #f0f2f5;"


st.markdown(f"""
<style>
    /* General App Styling */
    .stApp {{
        {bg_image_style}
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}

    /* Main content area with semi-transparent background for readability */
    .main .block-container {{
        background-color: rgba(240, 242, 245, 0.97); /* Semi-transparent background */
        padding: 2rem;
        border-radius: 10px;
    }}

    /* Larger Font Sizes */
    div.stButton > button:first-child {{
        background-color: #007bff;
        color: white;
        font-size: 1.5rem !important;
    }}
    body, .stTextInput, .stTextArea, .stSelectbox, .st-b3, .st-af {{
        font-size: 1.5rem !important; /* Increased base font size */
    }}
    h1 {{ font-size: 4.2rem !important; }}
    h2 {{ font-size: 3.4rem !important; }}
    h3 {{ font-size: 2.8rem !important; }}

    /* Bolder and Larger Tabs */
    .stTabs [data-baseweb="tab"] {{
        font-size: 1.6rem; /* Even larger tab font */
        font-weight: bold; /* Make tab font bold */
        padding: 12px 18px;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        background-color: #003366;
        color: white;
    }}

    /* Chat Container and Messaging Styles */
    .chat-container {{
        display: flex;
        flex-direction: column;
        max-height: 65vh;
        overflow-y: auto;
        padding: 15px;
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    .message-row {{
        display: flex;
        align-items: flex-start;
        margin-bottom: 15px;
        gap: 10px;
    }}
    .user-row {{
        justify-content: flex-end;
    }}
    .bot-row {{
        justify-content: flex-start;
    }}
    .avatar {{
        width: 50px;
        height: 50px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
    }}
    .user-avatar {{
        background-color: #007bff;
        color: white;
    }}
    .bot-avatar {{
        background-color: #e9ecef;
        color: #333;
    }}
    .chat-message {{
        padding: 16px 22px;
        border-radius: 20px;
        max-width: 70%;
        line-height: 1.6;
        font-size: 1.5rem; /* Larger chat message font */
    }}
    .user-message {{
        background-color: #007bff;
        color: white;
        border-top-right-radius: 0;
    }}
    .bot-message {{
        background-color: #e9ecef;
        color: #333;
        border-top-left-radius: 0;
    }}

    /* Timeline Styles */
    .timeline {{
        border-left: 3px solid #007bff;
        padding: 0 20px;
        list-style: none;
    }}
    .timeline-item {{
        position: relative;
        margin-bottom: 25px;
    }}
    .timeline-item::before {{
        content: '';
        position: absolute;
        left: -32px;
        top: 8px;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        background-color: white;
        border: 3px solid #007bff;
    }}
    .timeline-item.delivered::before {{
        background-color: #28a745;
        border-color: #28a745;
    }}
    .timeline-item-title {{
        font-weight: bold;
        color: #003366;
        font-size: 1.7rem; /* Larger timeline font */
    }}
    .timeline-item-date {{
        font-size: 1.4rem;
        color: #555;
    }}
    .timeline-item-details {{
        font-size: 1.4rem;
        color: #666;
    }}
</style>
""", unsafe_allow_html=True)

# --- DATA FILE HANDLING ---
def load_json_file(filename, default_content=None):
    if not os.path.exists(filename):
        content_to_write = default_content if default_content is not None else {}
        st.info(f"'{filename}' not found. Creating a new empty file.")
        with open(filename, 'w') as f:
            json.dump(content_to_write, f, indent=2)
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        st.error(f"Error loading or creating {filename}: {e}")
        return default_content if default_content is not None else {}

def write_json_file(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Failed to save data to {filename}: {e}")
        return False

# Load all data files
users_data = load_json_file("users.json", {"users": []})
orders_data = load_json_file("orders.json", {"orders": {}})
non_login_data = load_json_file("non_login.json", {"packages": {}})
claim_data = load_json_file("claim_package.json", {"claimed_packages": {}})
locations_data = load_json_file("locations.json", {})
# Load both pricing files
price_estimations_data = load_json_file("price_estimates.json", {})
zone_prices_data = load_json_file("prices.json", {}) # For zone-based fallback

# --- INITIALIZE SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = [{"role": "assistant", "content": "Hello! I'm the Sir Parcel AI Assistant."}]

# --- GEMINI API FUNCTION ---
async def get_gemini_response(user_prompt: str, package_data: dict):
    system_prompt = f"""
    You are "Sir Parcel AI", a friendly and helpful AI assistant for a courier company called "Sir Parcel".
    You have access to the follow  ving public package tracking data in JSON format:
    {json.dumps(package_data, indent=2)}
    """
    chat_history = [{"role": "user", "parts": [{"text": system_prompt}]}, {"role": "model", "parts": [{"text": "Understood. I am Sir Parcel AI, ready to help."}]}, {"role": "user", "parts": [{"text": user_prompt}]}]
    payload = {"contents": chat_history}
    apiKey = "AIzaSyC6WdCocMKXGtXk146k4NbA3yuaHQ-myyg"
    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={apiKey}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(apiUrl, json=payload, headers={'Content-Type': 'application/json'}, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            if (result.get('candidates') and result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts')):
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                return "I'm sorry, I couldn't process that request."
    except Exception as e:
        return f"An error occurred: {e}"

# --- Other Core Functions ---
def login(username, password):
    users_list = users_data.get('users', [])
    user = next((u for u in users_list if u.get('username') == username and u.get('password') == password), None)
    if user:
        st.session_state.logged_in = True
        st.session_state.user_info = user
        st.rerun()
    else:
        st.error("Invalid Username or Password.")

def logout():
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.rerun()

def add_new_user(username, password, full_name, address):
    current_users = load_json_file("users.json", {"users": []})
    if any(u.get('username') == username for u in current_users['users']):
        st.warning("Username already exists.")
        return
    current_users['users'].append({"username": username, "password": password, "full_name": full_name, "address": address})
    if write_json_file("users.json", current_users):
        st.success("Account created successfully! You can now log in.")

def claim_package(username, tracking_number, user_full_name, user_address):
    public_packages = load_json_file("non_login.json", {"packages": {}}).get('packages', {})
    full_orders = load_json_file("orders.json", {"orders": {}}).get('orders', {})
    claimed_packages = load_json_file("claim_package.json", {"claimed_packages": {}}).get('claimed_packages', {})
    if tracking_number in claimed_packages:
        st.warning(f"Package {tracking_number} has already been claimed.")
        return
    public_package_info = public_packages.get(tracking_number)
    if not public_package_info:
        st.error("This Waybill number was not found.")
        return
    new_order = {
        "username": username,
        "product": {"name": public_package_info.get("product_name", "N/A"), "price": "N/A"},
        "recipient": {"name": user_full_name, "address": user_address},
        "seller": public_package_info.get("seller", {}),
        "eta": public_package_info.get("eta", "N/A"),
        "timeline": [[e.get('status'), e.get('date'), [e.get('details')]] for e in public_package_info.get("timeline", [])]
    }
    full_orders[tracking_number] = new_order
    claimed_packages[tracking_number] = {"username": username, "claim_date": datetime.now().isoformat()}
    if write_json_file("orders.json", {"orders": full_orders}) and write_json_file("claim_package.json", {"claimed_packages": claimed_packages}):
        st.success(f"Package {tracking_number} added to your account!")
        time.sleep(1)
        st.rerun()

def forgot_password(username, new_password):
    current_users = load_json_file("users.json", {"users": []})
    user_found = False
    for user in current_users['users']:
        if user.get('username') == username:
            user['password'] = new_password
            user_found = True
            break
    if user_found:
        if write_json_file("users.json", current_users):
            st.success("Password updated successfully!")
    else:
        st.error("Username not found.")

def update_user_credentials(old_username, new_username, new_password, new_full_name, new_address):
    current_users = load_json_file("users.json", {"users": []})
    if new_username != old_username and any(u.get('username') == new_username for u in current_users['users']):
        st.warning("New username already exists.")
        return
    user_found = False
    for user in current_users['users']:
        if user.get('username') == old_username:
            user['username'] = new_username
            user['password'] = new_password
            user['full_name'] = new_full_name
            user['address'] = new_address
            user_found = True
            break
    if user_found:
        if write_json_file("users.json", current_users):
            st.success("Account details updated successfully. Please log in again.")
            logout()
    else:
        st.error("An error occurred.")

def create_invoice_pdf(order_details, order_id, is_public=False):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", 'B', 24)
    pdf.cell(0, 15, "INVOICE", 0, 1, 'L')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 6, "Sir Parcel", 0, 1, 'L')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, "123 Courier Lane, Tech City, 560001", 0, 1, 'L')
    pdf.cell(0, 5, "Phone: (080) 1234 5678", 0, 1, 'L')
    pdf.cell(0, 5, "Email: contact@sirparcel.com", 0, 1, 'L')
    pdf.set_y(25)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(130)
    pdf.cell(30, 7, "INVOICE NO.", 0, 0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(30, 7, order_id.replace("FMPP", ""), 0, 1)
    pdf.cell(130)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 7, "DATE", 0, 0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(30, 7, datetime.now().strftime('%B %d, %Y'), 0, 1)
    pdf.ln(10)
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 8, "BILL TO", 0, 0, 'L', True)
    pdf.cell(95, 8, "SHIP FROM", 0, 1, 'L', True)
    pdf.set_font("Arial", '', 10)
    seller = order_details.get('seller', {})
    ship_to_address = f"{seller.get('name', 'N/A')}\n{seller.get('address', 'N/A')}"
    if is_public:
        bill_to_address = "Valued Customer\n(Address details available upon login)"
    else:
        recipient = order_details.get('recipient', {})
        bill_to_address = f"{recipient.get('name', 'N/A')}\n{recipient.get('address', 'N/A')}"
    y_before = pdf.get_y()
    pdf.multi_cell(95, 6, bill_to_address, 0, 'L')
    y_after_bill = pdf.get_y()
    pdf.set_y(y_before)
    pdf.set_x(105)
    pdf.multi_cell(95, 6, ship_to_address, 0, 'L')
    y_after_ship = pdf.get_y()
    pdf.set_y(max(y_after_bill, y_after_ship))
    pdf.ln(5)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(20, 10, 'QTY', 1, 0, 'C', True)
    pdf.cell(110, 10, 'DESCRIPTION', 1, 0, 'C', True)
    pdf.cell(30, 10, 'UNIT COST', 1, 0, 'C', True)
    pdf.cell(30, 10, 'TOTAL', 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)
    if is_public:
        product_name = order_details.get('product_name', 'N/A')
        price = 0.0
    else:
        product = order_details.get('product', {})
        product_name = product.get('name', 'N/A')
        price_str = str(product.get('price', '0')).replace('Rs. ', '').replace(',', '')
        try:
            price = float(price_str)
        except ValueError:
            price = 0.0
    pdf.cell(20, 10, '1', 1, 0, 'C')
    pdf.cell(110, 10, product_name, 1, 0)
    pdf.cell(30, 10, f"{price:,.2f}" if not is_public else "N/A", 1, 0, 'R')
    pdf.cell(30, 10, f"{price:,.2f}" if not is_public else "N/A", 1, 1, 'R')
    if not is_public:
        subtotal = price
        tax = subtotal * 0.18
        total = subtotal + tax
        pdf.ln(5)
        pdf.set_x(120)
        pdf.set_font("Arial", '', 10)
        pdf.cell(40, 7, "SUBTOTAL", 0, 0, 'R')
        pdf.cell(40, 7, f"{subtotal:,.2f}", 0, 1, 'R')
        pdf.set_x(120)
        pdf.cell(40, 7, "TAX (18%)", 0, 0, 'R')
        pdf.cell(40, 7, f"{tax:,.2f}", 0, 1, 'R')
        pdf.set_x(120)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(40, 10, "TOTAL", 0, 0, 'R')
        pdf.cell(40, 10, f"Rs. {total:,.2f}", 0, 1, 'R')
    pdf.set_y(-30)
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Thank you for your business!", 0, 0, 'C')
    return pdf.output(dest='S').encode('latin-1')

def display_timeline(timeline_data):
    timeline_html = "<ul class='timeline'>"
    if not isinstance(timeline_data, list) or not all(isinstance(i, dict) for i in timeline_data):
        st.error("Timeline data is in an incorrect format.")
        return

    for i, event in enumerate(reversed(timeline_data)):
        status_with_emoji = event.get('status', 'N/A')
        status = ''.join(char for char in status_with_emoji if char.isprintable()).strip()
        date = event.get('date', 'N/A')
        details = event.get('details', 'N/A')
        item_class = 'timeline-item'
        if i == 0 and "Delivered" in status:
            item_class += ' delivered'
        timeline_html += f"""
        <li class='{item_class}'>
            <div class='timeline-item-title'>{status}</div>
            <div class='timeline-item-date'>{date}</div>
            <div class='timeline-item-details'>{details}</div>
        </li>"""
    timeline_html += "</ul>"
    st.markdown(timeline_html, unsafe_allow_html=True)

# --- Pricing Calculation Functions (UPDATED) ---
@st.cache_data
def get_all_cities(_locations, _price_estimations):
    """
    Extracts a sorted, unique list of all cities from both locations and price estimations data.
    """
    cities = set()
    # Get cities from locations file (for zone fallback)
    if isinstance(_locations, dict):
        for state in _locations.values():
            if isinstance(state, dict):
                cities.update(list(state.get("cities", {}).keys()))

    # Get cities from direct price estimations file
    if isinstance(_price_estimations, dict):
        cities.update(list(_price_estimations.keys()))
        for from_city, destinations in _price_estimations.items():
            if isinstance(destinations, dict):
                cities.update(list(destinations.keys()))
                
    return sorted(list(cities))

@st.cache_data
def get_city_details(city_name, _locations, _prices):
    """
    Finds the state and zone for a given city.
    """
    for state_name, state_data in _locations.items():
        if city_name in state_data.get("cities", {}):
            for zone, states_in_zone in _prices.get("zones", {}).items():
                if state_name in states_in_zone:
                    return {"state": state_name, "zone": zone}
    return None

def calculate_price(from_city, to_city, weight, _locations, _prices, _price_estimations):
    """
    Calculates the shipping price based on a set of pricing rules.
    It first checks for a direct, pre-defined price in the _price_estimations data.
    If no direct price is found, it falls back to a zone-based calculation.
    """
    # 1. Input validation
    if not all([from_city, to_city, weight > 0]):
        return None, "Missing input data for price calculation."

    # 2. Check for a direct price estimation first
    if from_city in _price_estimations and to_city in _price_estimations.get(from_city, {}):
        rates = _price_estimations[from_city][to_city]
        cost = rates.get("base_rate", 0) + (weight * rates.get("rate_per_kg", 0))
        return cost, f"Shipment from {from_city} to {to_city} (Direct Rate)."

    # 3. Fallback to zone-based pricing if no direct estimation is found
    from_details = get_city_details(from_city, _locations, _prices)
    to_details = get_city_details(to_city, _locations, _prices)

    if not from_details or not to_details:
        return None, f"Could not determine location details for '{from_city}' or '{to_city}' for zone-based pricing."

    from_state = from_details["state"]
    to_state = to_details["state"]
    from_zone = from_details["zone"]
    to_zone = to_details["zone"]

    pricing_tier = ""
    special_regions = _prices.get("special_regions", [])

    if from_state in special_regions or to_state in special_regions:
        pricing_tier = "special_region"
    elif from_zone == to_zone:
        pricing_tier = "intra_zone"
    elif to_zone in _prices.get("zone_adjacencies", {}).get(from_zone, []):
        pricing_tier = "adjacent_zone"
    else:
        pricing_tier = "national"

    rates = _prices.get("pricing", {}).get(pricing_tier)
    if not rates:
        return None, f"Pricing rates not found for tier: {pricing_tier}"

    cost = rates.get("base_rate", 0) + (weight * rates.get("rate_per_kg", 0))
    return cost, f"Shipment from {from_zone} Zone to {to_zone} Zone ({pricing_tier.replace('_', ' ').title()})."


# --- UI LAYOUT ---
st.title("Sir Parcel")
st.subheader("Your Premier Parcel & Logistics Partner")

with st.sidebar:
    if st.session_state.logged_in:
        st.subheader(f"Welcome, {st.session_state.user_info.get('full_name', 'User')}!")
        st.button("Logout", on_click=logout)
    else:
        st.subheader("Member Login")
        with st.form("login_form"):
            username_input = st.text_input("Username")
            password_input = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                login(username_input, password_input)

        with st.expander("Create a New Account"):
            with st.form("signup_form"):
                new_full_name = st.text_input("Full Name")
                new_address = st.text_area("Address")
                new_username = st.text_input("New Username")
                new_password = st.text_input("New Password", type="password")
                if st.form_submit_button("Create Account"):
                    if new_username and new_password and new_full_name and new_address:
                        add_new_user(new_username, new_password, new_full_name, new_address)
                    else:
                        st.warning("Please provide a Full Name, Address, Username, and Password.")

        with st.expander("Forgot Password?"):
            with st.form("forgot_password_form"):
                forgot_username = st.text_input("Enter your Username")
                new_password_forgot = st.text_input("Enter New Password", type="password")
                if st.form_submit_button("Reset Password"):
                    if forgot_username and new_password_forgot:
                        forgot_password(forgot_username, new_password_forgot)
                    else:
                        st.warning("Please provide your username and a new password.")

st.markdown("---")

# ADD "About Us" to the tab list
tab_list = ["📍 Track Parcel", "🏢 About Us", "💰 Get a Quote", "🏢 Find Location", "🚚 Schedule a Pickup", "🛠️ Tools", "🤖 AI Assistant"]
if st.session_state.logged_in:
    tab_list.insert(0, "👤 My Account")
tabs = st.tabs(tab_list)

# Unpack the tabs correctly based on login state
if st.session_state.logged_in:
    my_account_tab, track_tab, about_us_tab, quote_tab, location_tab, pickup_tab, tools_tab, assistant_tab = tabs
else:
    track_tab, about_us_tab, quote_tab, location_tab, pickup_tab, tools_tab, assistant_tab = tabs

if st.session_state.logged_in:
    with my_account_tab:
        st.header("My Account Dashboard")
        user = st.session_state.user_info
        st.write(f"**Username:** {user.get('username')}")
        st.write(f"**Full Name:** {user.get('full_name', 'N/A')}")
        st.write(f"**Address:** {user.get('address', 'N/A')}")

        with st.expander("Account Settings"):
            with st.form("update_account_form"):
                st.write("Update your account details. Leave password blank to keep it unchanged.")
                updated_full_name = st.text_input("Full Name", value=user.get('full_name'))
                updated_address = st.text_area("Address", value=user.get('address'))
                updated_username = st.text_input("Username", value=user.get('username'))
                updated_password = st.text_input("New Password", type="password", placeholder="Leave blank to keep current")

                if st.form_submit_button("Update Account"):
                    final_password = updated_password if updated_password else user.get('password')
                    if updated_username and updated_full_name and updated_address:
                        update_user_credentials(user.get('username'), updated_username, final_password, updated_full_name, updated_address)
                    else:
                        st.warning("Full Name, Address, and Username cannot be empty.")

        with st.expander("Claim a Package"):
            with st.form("claim_form"):
                claim_tracking_number = st.text_input("Enter Waybill Number to Claim")
                if st.form_submit_button("Claim Package"):
                    if claim_tracking_number:
                        claim_package(user.get('username'), claim_tracking_number, user.get('full_name'), user.get('address'))
                    else:
                        st.warning("Please enter a Waybill number.")

        st.subheader("My Order History")
        current_orders = load_json_file("orders.json", {"orders": {}}).get('orders', {})
        user_orders = {oid: details for oid, details in current_orders.items() if details.get('username') == user.get('username')}
        if not user_orders:
            st.info("No orders found for your account.")
        else:
            for order_id, order in user_orders.items():
                with st.container(border=True):
                    st.write(f"**Order ID:** {order_id}")
                    st.write(f"**Product:** {order.get('product', {}).get('name', 'N/A')}")
                    st.write(f"**Status:** {order.get('eta', 'N/A')}")

                    timeline_data_from_orders = order.get('timeline', [])
                    timeline_for_display = []
                    if timeline_data_from_orders and isinstance(timeline_data_from_orders[0], list):
                         timeline_for_display = [{"status": t[0], "date": t[1], "details": t[2][0]} for t in timeline_data_from_orders]
                    display_timeline(timeline_for_display)

                    pdf_bytes = create_invoice_pdf(order, order_id)
                    st.download_button(
                        label="Download Invoice (PDF)",
                        data=pdf_bytes,
                        file_name=f"invoice_{order_id}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{order_id}"
                    )

with track_tab:
    st.header("Track Your Shipment")
    public_packages = non_login_data.get('packages', {})
    tracking_number = st.text_input("Enter Waybill Number", key="public_waybill")
    if st.button("Track Public Package", key="public_track_button"):
        if tracking_number:
            package_info = public_packages.get(tracking_number)
            if package_info:
                st.success(f"Shipment found for **{tracking_number}**")
                st.metric("Product", package_info.get('product_name', 'N/A'))
                st.metric("Current Status", package_info.get('eta', 'N/A'))
                st.subheader("Shipment Timeline")
                display_timeline(package_info.get('timeline', []))
                pdf_bytes = create_invoice_pdf(package_info, tracking_number, is_public=True)
                st.download_button(
                    label="Download Proof of Delivery (PDF)",
                    data=pdf_bytes,
                    file_name=f"pod_{tracking_number}.pdf",
                    mime="application/pdf",
                    key=f"public_pdf_{tracking_number}"
                )
            else:
                st.error("No such Waybill number found.")
        else:
            st.warning("Please enter a Waybill number.")

# "About Us" Tab - MODIFIED
with about_us_tab:
    st.header("About Sir Parcel")
    st.image("https://placehold.co/800x300/003366/FFFFFF?text=Sir+Parcel&font=lato", use_column_width=True)
    st.markdown("""
    ### Our Mission
    At Sir Parcel, our mission is to provide reliable, efficient, and affordable logistics solutions that connect businesses and individuals across the nation. We are committed to leveraging technology to deliver excellence and build lasting relationships with our customers.
    """)
    st.markdown("---")
    st.subheader("**Meet the Team**")
    
    st.markdown("##### **joshuah vijay** - *Team Lead*")
    st.markdown("##### **Adhvik Vitun** - *Lead Developer*")
    st.markdown("##### **Sanjay kumar** - *UI/UX Designer*")

with quote_tab:
    st.header("Get a Price Estimate")
    
    # Generate the list of cities from all available data sources first.
    all_cities_list = get_all_cities(locations_data, price_estimations_data)
    
    # Check if we have any cities to work with.
    if not all_cities_list:
         st.error("Pricing and location data could not be loaded. Please ensure 'locations.json' and/or 'price_estimates.json' are present and contain data.")
    else:
        c1, c2 = st.columns(2)
        from_city = c1.selectbox("From", options=all_cities_list, index=None, placeholder="Select origin city")
        to_city = c2.selectbox("To", options=all_cities_list, index=None, placeholder="Select destination city")

        weight = st.number_input("Weight (kg)", min_value=0.1, value=1.0, step=0.5)

        if st.button("Calculate Cost"):
            if not from_city or not to_city:
                st.warning("Please select both an origin and a destination city.")
            elif from_city == to_city:
                st.warning("Origin and destination cities cannot be the same.")
            else:
                with st.spinner("Calculating..."):
                    # The calculate_price function already handles missing data gracefully.
                    cost, details = calculate_price(from_city, to_city, weight, locations_data, zone_prices_data, price_estimations_data)
                    if cost is not None:
                        st.success(f"**Estimated Cost: ₹ {cost:.2f}**")
                        st.info(f"ℹ️ Calculation details: {details}")
                    else:
                        st.error(f"Could not calculate the price. Reason: {details}")

with location_tab:
    st.header("Find a Sir Parcel Location")
    if not locations_data:
        st.error("Location data could not be loaded.")
    else:
        states = list(locations_data.keys())
        selected_state = st.selectbox("Select State", states, index=None, placeholder="Select a state")
        if selected_state:
            cities_data = locations_data[selected_state].get("cities", {})
            cities = list(cities_data.keys())
            if not cities:
                st.info(f"No cities found for {selected_state}.")
            else:
                selected_city = st.selectbox("Select City", cities, index=None, placeholder="Select a city")
                if selected_city:
                    city_info = cities_data[selected_city]
                    offices = city_info.get("offices", [])
                    st.subheader(f"Offices in {selected_city}")
                    if not offices:
                        st.info(f"No offices listed for {selected_city}.")
                    else:
                        for loc in offices:
                            with st.container(border=True):
                                st.write(f"**Address:** {loc.get('address', 'N/A')}")
                                st.write(f"**Contact:** {loc.get('contact', 'N/A')}")

with pickup_tab:
    st.header("Schedule a Pickup")
    with st.form("pickup_form"):
        st.subheader("Shipper Details")
        shipper_name = st.text_input("Your Name")
        shipper_address = st.text_area("Your Full Address")
        shipper_pincode = st.text_input("Your Pincode", max_chars=6)
        shipper_phone = st.text_input("Your Mobile Number")
        st.markdown("---")
        st.subheader("Recipient Details")
        recipient_name = st.text_input("Recipient's Name")
        recipient_address = st.text_area("Recipient's Full Address")
        recipient_pincode = st.text_input("Recipient's Pincode", max_chars=6)
        st.markdown("---")
        st.subheader("Package Details")
        package_desc = st.text_input("Description of Contents")
        package_weight = st.number_input("Weight (kg)", min_value=0.1, value=0.5, step=0.1)
        st.markdown("---")
        st.subheader("Pickup Time")
        pickup_date = st.date_input("Preferred Pickup Date", min_value=datetime.today())
        pickup_submitted = st.form_submit_button("Book Pickup")
        if pickup_submitted:
            if all([shipper_name, shipper_address, shipper_pincode, shipper_phone, recipient_name, recipient_address, recipient_pincode, package_desc]):
                if not (shipper_pincode.isdigit() and len(shipper_pincode) == 6 and recipient_pincode.isdigit() and len(recipient_pincode) == 6):
                    st.error("Please enter valid 6-digit pincodes for both shipper and recipient.")
                else:
                    with st.spinner("Booking your pickup..."):
                        time.sleep(2)
                    st.success(f"Thank you, {shipper_name}! Your pickup for '{package_desc}' has been scheduled for {pickup_date.strftime('%d-%b-%Y')}. Our agent will contact you shortly.")
            else:
                st.warning("Please fill in all the required fields.")

with tools_tab:
    st.header("Courier Tools & Information")
    st.markdown("---")
    with st.expander("🚫 Prohibited & Banned Items"):
        st.markdown("""
        - Aerosols, Perfumes & Flammable items.
        - Batteries and electronic items with batteries.
        - Currency, Bullion, and Valuables.
        - Liquids and Semi-liquids.
        - Narcotics and Psychotropic substances.
        - Radioactive material.
        - Corrosives and Explosives.
        """)
    with st.expander("📦 How to Pack Your Parcel"):
        st.subheader("General Guidelines")
        st.markdown("""
        1.  **Choose the Right Box:** Select a new, rigid cardboard box that is slightly larger than your item.
        2.  **Cushion Your Item:** Wrap your item with at least 2 inches of cushioning (like bubble wrap) on all sides.
        3.  **Fill Empty Space:** Use packing peanuts, crumpled paper, or air pillows to fill any voids in the box to prevent shifting.
        4.  **Seal Securely:** Use strong packing tape (not masking or cellophane tape) to seal all seams and edges of the box.
        5.  **Label Clearly:** Place the shipping label on the largest, flattest side of the box. Ensure it's clearly visible and not obscured.
        """)
        st.subheader("Packing Specific Items")
        pack_c1, pack_c2 = st.columns(2)
        with pack_c1:
            st.markdown("**Electronics (Laptops, Phones):**")
            st.markdown("- Use the original manufacturer's packaging if possible.\n- If not, wrap the item in anti-static bubble wrap.\n- Place it in a sturdy box with ample cushioning.")
        with pack_c2:
            st.markdown("**Fragile Items (Glass, Ceramics):**")
            st.markdown("- Wrap each item individually in bubble wrap.\n- Use a double-walled box for extra protection.\n- Mark the box clearly with 'FRAGILE' on all sides.")
        st.subheader("Visual Guide")
        st.video("https://www.youtube.com/watch?v=WEJ_bS_9E-E") # Example video
    st.markdown("---")
    st.subheader("Measurement & Volumetric Weight Calculator")
    v_c1, v_c2, v_c3 = st.columns(3)
    length = v_c1.number_input("Length (cm)", min_value=1.0, step=1.0)
    width = v_c2.number_input("Width (cm)", min_value=1.0, step=1.0)
    height = v_c3.number_input("Height (cm)", min_value=1.0, step=1.0)
    if st.button("Calculate Volumetric Weight"):
        volumetric_weight = (length * width * height) / 5000.0
        st.success(f"**Volumetric Weight: {volumetric_weight:.2f} kg**")

with assistant_tab:
    st.header("🤖 AI Assistant")
    chat_display_container = st.container()
    with chat_display_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="message-row user-row">
                    <div class="chat-message user-message">{msg['content']}</div>
                    <div class="avatar user-avatar">👤</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="message-row bot-row">
                    <div class="avatar bot-avatar">🤖</div>
                    <div class="chat-message bot-message">{msg['content']}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    if prompt := st.chat_input("Ask the AI Assistant..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.spinner("AI is thinking..."):
            response = asyncio.run(get_gemini_response(prompt, non_login_data))
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
        st.rerun()
