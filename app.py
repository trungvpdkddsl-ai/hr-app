import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
from datetime import datetime, date
import qrcode
from io import BytesIO
import requests
import base64

# --- CẤU HÌNH ---
st.set_page_config(page_title="HR System Pro", layout="wide", page_icon="💎")

# Link Apps Script của bạn (Đã điền sẵn)
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzKueqCnPonJ1MsFzQpQDk7ihgnVVQyNHMUyc_dx6AocsDu1jW1zf6Gr9VgqMD4D00/exec"

# --- CSS GIAO DIỆN ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {background-color: #f8f9fa;}
    [data-testid="stSidebar"] .stButton > button {
        width: 100%; height: 50px; border: none; border-radius: 8px;
        background-color: white; color: #333; font-weight: 600;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: left; padding-left: 15px; margin-bottom: 5px;
    }
    [data-testid="stSidebar"] .stButton > button:hover {background-color: #e3f2fd; color: #1565c0;}
    
    /* Style cho link tải ảnh */
    .download-link {
        display: inline-block; padding: 5px 10px; background-color: #4CAF50; color: white !important; 
        text-decoration: none; border-radius: 4px; font-size: 12px; margin-top: 5px;
    }
    .download-link:hover {background-color: #45a049;}
    </style>
""", unsafe_allow_html=True)

# --- KẾT NỐI ---
@st.cache_resource
def get_gcp_service():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        return client
    except: return None

client = get_gcp_service()
if not client: st.error("⚠️ Lỗi kết nối Secrets!"); st.stop()

# MỞ SHEET
try:
    sheet_ungvien = client.open("TuyenDungKCN_Data").worksheet("UngVien")
    sheet_users = client.open("TuyenDungKCN_Data").worksheet("Users")
    try: sheet_storage = client.open("TuyenDungKCN_Data").worksheet("KhoAnh")
    except: sheet_storage = None
    try: sheet_templates = client.open("TuyenDungKCN_Data").worksheet("MauBai")
    except: sheet_templates = None
except: st.error("⚠️ Không tìm thấy file Excel."); st.stop()

# --- CÁC HÀM HỖ TRỢ XỬ LÝ ẢNH ---
def upload_via_appsscript(file_obj, file_name):
    try:
        file_bytes = file_obj.getvalue()
        base64_str = base64.b64encode(file_bytes).decode('utf-8')
        payload = {"base64": base64_str, "filename": file_name, "mimeType": file_obj.type}
        response = requests.post(APPS_SCRIPT_URL, json=payload)
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("result") == "success": return res_json.get("link")
    except: pass
    return None

def convert_drive_link(link):
    """Chuyển link Drive thường thành link xem trực tiếp (Thumbnail High Res)"""
    if "id=" in link:
        file_id = link.split("id=")[1]
        # Link này Google cho phép load ảnh nhanh và không bị chặn
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000" 
    return link

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO(); img.save(buf)
    return buf.getvalue()

# --- SESSION ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_page' not in st.session_state: st.session_state.current_page = "dashboard"
def set_page(page_name): st.session_state.current_page = page_name

# --- LOGIN ---
def login_screen():
    st.markdown("<br><h1 style='text-align: center; color:#1565c0'>🔐 HR SYSTEM PRO</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        tab1, tab2 = st.tabs(["ĐĂNG NHẬP", "ĐĂNG KÝ"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Username"); p = st.text_input("Password", type="password")
                if st.form_submit_button("VÀO HỆ THỐNG", use_container_width=True):
                    users = sheet_users.get_all_records()
                    found = False
                    for user in users:
                        if str(user['Username']) == u and str(user['Password']) == p:
                            st.session_state.logged_in = True; st.session_state.user_role = user['Role']
                            st.session_state.user_name = user['HoTen']; found = True; st.rerun()
                    if not found: st.error("Sai thông tin!")
        with tab2:
            with st.form("reg"):
                nu = st.text_input("User mới"); np = st.text_input("Pass mới", type="password"); nn = st.text_input("Họ tên")
                if st.form_submit_button("TẠO TÀI KHOẢN", use_container_width=True):
                    existing = sheet_users.col_values(1)
                    if nu in existing: st.warning("Tên tồn tại!")
                    else: sheet_users.append_row([nu, np, "staff", nn]); st.success("OK! Mời đăng nhập.")

# --- MAIN APP ---
def main_app():
    df = pd.DataFrame(sheet_ungvien.get_all_records())

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"Role: {st.session_state.user_role.upper()}")
        st.markdown("---")
        if st.button("🏠 DASHBOARD"): set_page("dashboard")
        if st.button("📝 NHẬP HỒ SƠ"): set_page("input")
        if st.button("🔍 DANH SÁCH"): set_page("list")
        if st.button("📋 MẪU CONTENT"): set_page("templates")
        if sheet_storage:
            if st.button("🖼️ KHO ẢNH"): set_page("storage")
        if st.session_state.user_role == "admin":
            st.markdown("---"); 
            if st.button("⚙️ QUẢN TRỊ"): set_page("admin")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất"): st.session_state.logged_in = False; st.rerun()

    # 1. DASHBOARD
    if st.session_state.current_page == "dashboard":
        st.title("📊 Tổng Quan")
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Tổng Hồ Sơ", len(df))
            with c2: st.metric("Đã Đi Làm", len(df[df['TrangThai']=='Đã đi làm']))
            with c3: st.metric("Mới Nhận", len(df[df['TrangThai']=='Mới nhận']))
            st.markdown("---")
            c4, c5 = st.columns([2, 1])
            with c4: 
                st.subheader("🏆 Top Tuyển Dụng")
                if 'NguoiTuyen' in df.columns: st.bar_chart(df['NguoiTuyen'].value_counts())
            with c5: 
                st.subheader("🎯 Nguồn"); st.dataframe(df['Nguồn'].value_counts(), use_container_width=True)

    # 2. NHẬP LIỆU
    elif st.session_state.current_page == "input":
        st.header("📝 Nhập Hồ Sơ")
        with st.form("input_form"):
            col_img, col_info = st.columns([1, 3])
            with col_img:
                uploaded_file = st.file_uploader("Upload ảnh (3x4)", type=['jpg','png','jpeg'])
            with col_info:
                name = st.text_input("Họ tên (*)")
                phone = st.text_input("SĐT (*)")
                cccd = st.text_input("CCCD (*)")

            r1, r2, r3 = st.columns(3)
            dob = r1.date_input("Ngày sinh", value=date(2000, 1, 1), min_value=date(1960, 1, 1))
            hometown = r2.text_input("Quê quán")
            pos = r3.selectbox("Vị trí", ["Công nhân", "Kỹ thuật", "Kho", "Bảo vệ", "Tạp vụ", "Khác"])
            
            r4, r5 = st.columns(2)
            source = r4.selectbox("Nguồn", ["Facebook", "Zalo", "Trực tiếp"])
            img_link_backup = r5.text_input("Link ảnh dự phòng (Nếu không upload)")

            st.markdown("---")
            fb = st.text_input("Link Facebook"); tt = st.text_input("Link TikTok")
            r6, r7, r8 = st.columns(3)
            bus = r6.selectbox("Xe tuyến", ["Tự túc", "Tuyến A", "Tuyến B"])
            doc = r7.selectbox("Giấy tờ", ["Chưa có", "Đủ giấy tờ"])
            ktx = r8.selectbox("Ký túc xá", ["Không", "Có"])

            if st.form_submit_button("LƯU HỒ SƠ", type="primary"):
                if name and phone and cccd:
                    with st.spinner("Đang xử lý ảnh..."):
                        final_link = img_link_backup 
                        if uploaded_file:
                            link_drive = upload_via_appsscript(uploaded_file, f"{name}_{phone}.jpg")
                            if link_drive: final_link = link_drive
                        
                        row = [datetime.now().strftime("%d/%m/%Y"), name.upper(), dob.strftime("%d/%m/%Y"), hometown, 
                               f"'{phone}", f"'{cccd}", pos, "Mới nhận", "", source, final_link, bus, ktx, 
                               st.session_state.user_name, fb, tt, doc]
                        sheet_ungvien.append_row(row)
                        st.success("✅ Thành công!"); time.sleep(1); st.rerun()
                else: st.error("Thiếu thông tin!")

    # 3. DANH SÁCH (ẢNH + TẢI VỀ)
    elif st.session_state.current_page == "list":
        st.header("🔍 Tra Cứu")
        if not df.empty:
            search = st.text_input("🔎 Tìm kiếm:")
            df_show = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else df
            
            # Bảng tổng quan
            st.dataframe(df_show[['HoTen', 'SDT', 'ViTri', 'TrangThai']], use_container_width=True, hide_index=True)
            
            st.write("### Chi tiết hồ sơ:")
            for i, row in df_show.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        # LOGIC HIỂN THỊ ẢNH MỚI
                        raw_link = str(row.get('LinkAnh', ''))
                        if raw_link and raw_link.startswith('http'):
                            # 1. Hiển thị ảnh (dùng link thumbnail cho nhanh)
                            thumb_link = convert_drive_link(raw_link)
                            st.image(thumb_link, width=120)
                            
                            # 2. Nút tải về (Dùng link gốc)
                            st.markdown(f'<a href="{raw_link}" target="_blank" class="download-link">📥 Tải ảnh gốc</a>', unsafe_allow_html=True)
                        else:
                            st.info("No Image")
                            
                    with c2:
                        st.markdown(f"#### {row['HoTen']} ({row['NamSinh']})")
                        st.write(f"📞 {row['SDT']} | 🆔 {row.get('CCCD')}")
                        st.write(f"🏠 {row['QueQuan']}")

    # 4. KHO ẢNH (ẢNH + TẢI VỀ)
    elif st.session_state.current_page == "storage" and sheet_storage:
        st.header("🖼️ Kho Ảnh Marketing")
        with st.form("up_store"):
            f = st.file_uploader("Upload ảnh"); t = st.text_input("Tên ảnh"); n = st.text_area("Ghi chú")
            if st.form_submit_button("Lưu"):
                if f and t:
                    with st.spinner("Uploading..."):
                        l = upload_via_appsscript(f, f"MKT_{t}.jpg")
                        if l: sheet_storage.append_row([datetime.now().strftime("%d/%m/%Y"), t, l, n]); st.success("OK!"); st.rerun()
        
        st.markdown("---")
        data = sheet_storage.get_all_records()
        if data:
            cols = st.columns(3)
            for idx, d in enumerate(data):
                with cols[idx%3]:
                    with st.container(border=True):
                        raw_link = d.get('LinkAnh', '')
                        if raw_link: 
                            thumb_link = convert_drive_link(raw_link)
                            st.image(thumb_link, use_container_width=True)
                            st.markdown(f"**{d['TenAnh']}**")
                            # Link tải về
                            st.markdown(f'<a href="{raw_link}" target="_blank" class="download-link">📥 Tải về máy</a>', unsafe_allow_html=True)
                            
                        with st.expander("Ghi chú"): st.write(d.get('GhiChu'))

    # 5. MẪU CONTENT
    elif st.session_state.current_page == "templates" and sheet_templates:
        st.header("📋 Mẫu Content")
        with st.expander("➕ Thêm mẫu"):
            with st.form("nt"):
                tt = st.text_input("Tiêu đề"); ct = st.text_area("Nội dung")
                if st.form_submit_button("Lưu"): sheet_templates.append_row([tt, ct, datetime.now().strftime("%d/%m/%Y")]); st.rerun()
        data = sheet_templates.get_all_records()
        for d in data:
            with st.container(border=True):
                st.subheader(d['TieuDe']); st.code(d['NoiDung'], language='text')

    # 6. ADMIN
    elif st.session_state.current_page == "admin":
        st.header("⚙️ Admin"); users = sheet_users.get_all_records(); st.dataframe(users)
        with st.form("rl"):
            u = st.selectbox("User", [x['Username'] for x in users]); r = st.selectbox("Role", ["staff", "admin"])
            if st.form_submit_button("Update"): cell = sheet_users.find(u); sheet_users.update_cell(cell.row, 3, r); st.success("Done!"); st.rerun()

# --- RUN ---
if st.session_state.logged_in: main_app()
else: login_screen()
