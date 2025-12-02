# streamlit_app_full.py
# Single-file Streamlit UI for Own_do backend
# Option A: includes st.rerun() to immediately refresh UI after actions
# Features: Login, Register (admin), Categories CRUD, Products CRUD,
# Add to Cart, View Cart, Place Order, List Orders (filter/pagination),
# Update order status (admin), Cancel order (owner/admin), List active sessions (admin)

import streamlit as st
import requests
from typing import Optional

# ------------ CONFIG ------------
API_URL = "http://127.0.0.1:8000"  # change if your FastAPI is hosted elsewhere
st.set_page_config(page_title="Own_do Dashboard", layout="wide")

# ------------ SESSION STATE ------------
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None   # raw token string from backend
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "email" not in st.session_state:
    st.session_state.email = None
if "page" not in st.session_state:
    st.session_state.page = "Login"

# ------------ HELPERS ------------
def auth_headers():
    headers = {}
    if st.session_state.auth_token:
        # Ensure we send Bearer <token> (HTTPBearer expected)
        token = st.session_state.auth_token
        if not token.startswith("Bearer "):
            headers["Authorization"] = f"Bearer {token}"
        else:
            headers["Authorization"] = token
    if st.session_state.session_id:
        headers["Session_id"] = st.session_state.session_id
    return headers

def do_request(method: str, path: str, json: Optional[dict] = None, params: Optional[dict] = None, expect_json=True):
    url = API_URL.rstrip("/") + path
    try:
        resp = requests.request(method, url, json=json, params=params, headers=auth_headers(), timeout=10)
    except Exception as e:
        return False, f"Request failed: {e}", None
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    ok = 200 <= resp.status_code < 300
    return ok, body, resp.status_code

def set_auth_from_login(resp_json, resp_headers=None):
    # resp_json is JSON returned by your /User_setup/login (contains auth_token, session_id, user_role, email)
    if not isinstance(resp_json, dict):
        return
    token = resp_json.get("auth_token") or resp_json.get("access_token")
    sid = resp_json.get("session_id")
    role = resp_json.get("user_role") or resp_json.get("role")
    email = resp_json.get("email")
    if token:
        # store token as-is (we will prefix with Bearer on requests)
        st.session_state.auth_token = token
    if sid:
        st.session_state.session_id = sid
    if role:
        st.session_state.user_role = role
    if email:
        st.session_state.email = email

# ------------ UI: Topbar / Sidebar ------------
st.title("Own_do — Admin & User Dashboard")

with st.sidebar:
    st.header("Navigation")
    if st.session_state.auth_token:
        st.success(f"{st.session_state.email} ({st.session_state.user_role})")
        # menu visible only when logged in
        page = st.radio("Go to", [
            "Home", "Products", "Categories", "Cart", "Orders", "Admin", "Sessions", "Logout"
        ], index=["Home","Products","Categories","Cart","Orders","Admin","Sessions","Logout"].index(st.session_state.page) if st.session_state.page in ["Home","Products","Categories","Cart","Orders","Admin","Sessions","Logout"] else 0)
    else:
        # when not logged in, only login & register pages visible
        page = st.radio("Go to", ["Login", "Register"], index=0)
    st.session_state.page = page
    st.markdown("---")
    st.write("API URL:")
    new_api = st.text_input("", API_URL)
    if new_api and new_api != API_URL:
        st.write("Note: Update API_URL in file if needed.")
    st.caption("Built for your Own_do FastAPI backend")

# ------------ PAGES IMPLEMENTATION ------------

# ---------- LOGIN ----------
def page_login():
    st.header("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login"):
        ok, body, code = do_request("POST", "/User_setup/login", json={"email": email, "password": password})
        if ok:
            set_auth_from_login(body)
            st.success("Login successful.")
            # store headers if server sets them (request already returned JSON, but sometimes server also sets headers)
            st.rerun()
        else:
            st.error(f"Login failed: {body}")

# ---------- REGISTER ----------
def page_register():
    st.header("Register (Admin Only)")
    # Only admin can create users, but if no admin exists backend allows creation (your register logic)
    username = st.text_input("Username", key="reg_username")
    email = st.text_input("Email", key="reg_email")
    password = st.text_input("Password", type="password", key="reg_password")
    contact = st.text_input("Contact number", key="reg_contact")
    role = st.selectbox("Role", ["user", "admin"], key="reg_role")
    if st.button("Register"):
        payload = {"username": username, "email": email, "password": password, "contact_number": contact, "role": role}
        ok, body, code = do_request("POST", "/User_setup/register", json=payload)
        if ok:
            st.success("User registered successfully.")
            st.rerun()
        else:
            st.error(f"Register failed: {body}")

# ---------- PRODUCTS (list, add, edit, delete, add-to-cart for users) ----------
def page_products():
    st.header("Products")
    # Fetch products (admin_or_user dependency required on backend)
    ok, body, code = do_request("GET", "/products/list")
    if not ok:
        st.error(f"Could not fetch products: {body}")
        return

    # response body format from backend: { "message": "...", "count": n, "data": [ {id,name,stock,is_active}, ... ] }
    data = body if isinstance(body, dict) else {}
    prod_list = data.get("data") if isinstance(data, dict) else None
    if prod_list is None:
        prod_list = []
    st.subheader("Available Products")
    for p in prod_list:
        # p might not include price/description depending on your backend's list implementation
        pid = p.get("id")
        name = p.get("name", "<no-name>")
        stock = p.get("stock", 0)
        is_active = p.get("is_active", False)
        price = p.get("price") if "price" in p else None  # may be missing in list endpoint
        row = st.columns([4, 1, 1, 2])
        price_str = f"Price: {price}" if price is not None else "Price: N/A"
        row[0].write(f"**{name}** (ID: {pid}) — Stock: {stock} — Active: {is_active} — {price_str}")
        # Admin CRUD
        if st.session_state.user_role == "admin":
            if row[1].button("Edit", key=f"edit_prod_{pid}"):
                with st.expander(f"Edit product {pid}", expanded=True):
                    new_name = st.text_input("Name", value=name, key=f"edit_name_{pid}")
                    new_price = st.number_input("Price", min_value=0.0, value=float(price) if price else 0.0, key=f"edit_price_{pid}")
                    new_stock = st.number_input("Stock", min_value=0, value=int(stock), key=f"edit_stock_{pid}")
                    # Note: backend endpoint path for update is /products/update/{product_id}
                    if st.button("Save changes", key=f"save_prod_{pid}"):
                        payload = {"name": new_name, "price": new_price, "stock": new_stock}
                        ok2, body2, code2 = do_request("PATCH", f"/products/update/{pid}", json=payload)
                        if ok2:
                            st.success("Product updated")
                            st.rerun()
                        else:
                            st.error(f"Update failed: {body2}")
            if row[2].button("Delete", key=f"del_prod_{pid}"):
                ok2, body2, code2 = do_request("DELETE", f"/products/delete/{pid}")
                if ok2:
                    st.success("Product marked inactive")
                    st.rerun()
                else:
                    st.error(f"Delete failed: {body2}")
        # User: add to cart
        if st.session_state.user_role == "user":
            qty_key = f"qty_{pid}"
            if qty_key not in st.session_state:
                st.session_state[qty_key] = 1
            qty = row[3].number_input("Qty", min_value=1, max_value=stock if stock>=1 else 1, value=st.session_state[qty_key], key=qty_key)
            if row[3].button("Add to cart", key=f"addcart_{pid}"):
                payload = {"product_id": pid, "qty": qty}
                ok2, body2, code2 = do_request("POST", "/carts/add", json=payload)
                if ok2:
                    st.success(f"Added {qty} x {name} to cart")
                else:
                    st.error(f"Add to cart failed: {body2}")
    # Admin: Add product form
    if st.session_state.user_role == "admin":
        st.markdown("---")
        st.subheader("Add new product")
        p_name = st.text_input("Name", key="new_prod_name")
        p_category = st.number_input("Category ID", min_value=1, step=1, key="new_prod_cat")
        p_price = st.number_input("Price", min_value=0.0, step=0.01, key="new_prod_price")
        p_stock = st.number_input("Stock", min_value=0, step=1, key="new_prod_stock")
        p_images = st.text_input("Image URLs (comma separated)", key="new_prod_images")
        if st.button("Create Product"):
            payload = {"category_id": int(p_category), "name": p_name, "description": "", "price": float(p_price), "stock": int(p_stock), "image_urls": [u.strip() for u in p_images.split(",") if u.strip()]}
            ok2, body2, code2 = do_request("POST", "/products/create_product", json=payload)
            if ok2:
                st.success("Product created")
                st.rerun()
            else:
                st.error(f"Create product failed: {body2}")

# ---------- CATEGORIES (list, add, update, delete) ----------
def page_categories():
    st.header("Categories")
    ok, body, code = do_request("GET", "/categories/list_category")
    if not ok:
        st.error(f"Could not fetch categories: {body}")
        return
    cats = body.get("returning_category") if isinstance(body, dict) else []
    for c in cats:
        cid = c.get("id")
        name = c.get("name")
        active = c.get("is_active")
        cols = st.columns([4,1,1])
        cols[0].write(f"**{name}** (ID: {cid}) — Active: {active}")
        if st.session_state.user_role == "admin":
            if cols[1].button("Edit", key=f"edit_cat_{cid}"):
                new_name = st.text_input("New name", value=name, key=f"new_cat_name_{cid}")
                if st.button("Save", key=f"save_cat_{cid}"):
                    ok2, body2, code2 = do_request("PUT", f"/categories/update_category/{cid}", json={"name": new_name})
                    if ok2:
                        st.success("Category updated")
                        st.rerun()
                    else:
                        st.error(f"Update failed: {body2}")
            if cols[2].button("Delete", key=f"del_cat_{cid}"):
                ok2, body2, code2 = do_request("DELETE", f"/categories/delete_category/{cid}")
                if ok2:
                    st.success("Category soft-deleted")
                    st.rerun()
                else:
                    st.error(f"Delete failed: {body2}")
    if st.session_state.user_role == "admin":
        st.markdown("---")
        st.subheader("Add Category")
        new_cat = st.text_input("Category name", key="new_cat_name")
        if st.button("Create Category"):
            ok2, body2, code2 = do_request("POST", "/categories/create_category", json={"name": new_cat})
            if ok2:
                st.success("Category created")
                st.rerun()
            else:
                st.error(f"Create failed: {body2}")

# ---------- CART (view, remove, place order) ----------
def page_cart():
    st.header("My Cart")
    ok, body, code = do_request("GET", "/carts/view")
    if not ok:
        st.info("Cart is empty or cannot be fetched")
        return
    data = body.get("data", {}) if isinstance(body, dict) else {}
    cart_id = data.get("id")
    items = data.get("items", [])
    if not items:
        st.info("Cart is empty")
    else:
        total_sum = 0.0
        for it in items:
            price = float(it.get("price_snapshot", 0))
            qty = int(it.get("qty", 0))
            total_sum += price * qty
            st.write(f"- Product ID {it.get('product_id')} — qty: {qty} — price_snapshot: {price}")
        st.write(f"**Total: {total_sum}**")
        if st.button("Place order"):
            ok2, body2, code2 = do_request("POST", "/carts/place")
            if ok2:
                st.success("Order placed successfully")
                st.rerun()
            else:
                st.error(f"Place order failed: {body2}")
    # allow removal by product id
    st.markdown("---")
    st.subheader("Remove item from cart")
    rem_pid = st.number_input("Product ID to remove", min_value=1, step=1, key="rem_pid")
    if st.button("Remove item"):
        ok2, body2, code2 = do_request("DELETE", f"/carts/remove/{int(rem_pid)}")
        if ok2:
            st.success("Item removed")
            st.rerun()
        else:
            st.error(f"Remove failed: {body2}")

# ---------- ORDERS (list, get by id, filter, update status admin, cancel) ----------
def page_orders():
    st.header("Orders")
    col1, col2, col3 = st.columns([3,3,2])
    order_id = col1.number_input("Order ID (optional)", min_value=0, step=1, value=0)
    status_filter = col2.selectbox("Status filter", ["all", "pending", "confirmed", "shipped", "delivered", "cancelled"])
    page = col3.number_input("Page", min_value=1, step=1, value=1)
    limit = 10
    params = {}
    if order_id:
        params["order_id"] = int(order_id)
    if status_filter != "all":
        params["status_filter"] = status_filter
    params["page"] = page
    params["limit"] = limit
    ok, body, code = do_request("GET", "/carts/orders", params=params)
    if not ok:
        st.error(f"Failed to fetch orders: {body}")
        return
    # Response structure includes total_orders, orders list etc.
    total = body.get("total_orders") or body.get("count") or 0
    st.write(f"Total orders (filtered): {total}")
    orders = body.get("orders") or body.get("data") or []
    for o in orders:
        with st.expander(f"Order #{o.get('id')} — status {o.get('status')}"):
            st.json(o)
            # if admin allow status update
            if st.session_state.user_role == "admin":
                new_status = st.selectbox(f"Set status for order {o.get('id')}", ["pending", "confirmed", "shipped", "delivered", "cancelled"], key=f"upd_{o.get('id')}")
                if st.button("Update status", key=f"upd_btn_{o.get('id')}"):
                    ok2, body2, code2 = do_request("PATCH", f"/carts/orders/{int(o.get('id'))}/status", json={"status": new_status})
                    if ok2:
                        st.success("Status updated")
                        st.rerun()
                    else:
                        st.error(f"Update failed: {body2}")
            # cancellation: users can cancel their own if allowed, admin can cancel any
            if st.session_state.user_role in ("admin", "user"):
                if st.button("Cancel this order", key=f"cancel_btn_{o.get('id')}"):
                    ok2, body2, code2 = do_request("PATCH", f"/carts/orders/{int(o.get('id'))}/cancel")
                    if ok2:
                        st.success("Order cancelled")
                        st.rerun()
                    else:
                        st.error(f"Cancel failed: {body2}")

# ---------- ADMIN - list active sessions ----------
def page_sessions():
    st.header("Active Login Sessions (admin)")
    ok, body, code = do_request("GET", "/List_active_sessions/list_Login_sessions_active")
    if not ok:
        st.error(f"Failed: {body}")
        return
    st.json(body)

# ---------- HOME ----------
def page_home():
    st.header("Home")
    st.write("Welcome to Own_do admin/user dashboard. Use the sidebar navigation to access features.")

# ---------- LOGOUT ----------
def do_logout():
    # call logout to deactivate session on server if session_id present
    sid = st.session_state.session_id
    if sid:
        ok, body, code = do_request("POST", "/User_setup/logout", json={"session_id": sid})
    # clear local session
    st.session_state.auth_token = None
    st.session_state.session_id = None
    st.session_state.user_role = None
    st.session_state.email = None
    st.success("Logged out")
    st.rerun()

# ------------ PAGE ROUTING ------------
page = st.session_state.page

if page == "Login":
    page_login()
elif page == "Register":
    page_register()
elif page == "Products":
    if not st.session_state.auth_token:
        st.warning("Please login first")
    else:
        page_products()
elif page == "Categories":
    if not st.session_state.auth_token:
        st.warning("Please login first")
    else:
        page_categories()
elif page == "Cart":
    if not st.session_state.auth_token:
        st.warning("Please login first")
    else:
        page_cart()
elif page == "Orders":
    if not st.session_state.auth_token:
        st.warning("Please login first")
    else:
        page_orders()
elif page == "Admin":
    if not st.session_state.auth_token:
        st.warning("Please login first")
    elif st.session_state.user_role != "admin":
        st.error("Admins only")
    else:
        page_home()
elif page == "Sessions":
    if not st.session_state.auth_token:
        st.warning("Please login first")
    elif st.session_state.user_role != "admin":
        st.error("Admins only")
    else:
        page_sessions()
elif page == "Logout":
    do_logout()
else:
    page_home()
