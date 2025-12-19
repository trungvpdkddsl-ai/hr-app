import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import time
from datetime import datetime
import qrcode
from io import BytesIO

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="HR Admin Pro", layout="wide", page_icon="👔")

# --- CẤU HÌNH ID DRIVE ---
FOLDER_ID_DRIVE = "1Sw91t5o-m8fwZsbGpJw8Yex_WzV8etCx"

# --- CSS BIẾN HÓA GIAO DIỆN ---
st.markdown("""
    <style>
    /* 1. TÙY BIẾN THANH SIDEBAR BÊN TRÁI */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #dee2e6;
    }
    
    /* Biến các nút bấm trong Sidebar thành dạng KHỐI VUÔNG đẹp mắt */
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        height: 60px; /* Chiều cao nút */
        border: none;
        border-radius: 10px;
        background-color: white;
        color: #495057;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: left;
        padding-left: 20px;
        transition: all 0.3s;
        margin-bottom: 10px;
    }
    
    /* Hiệu ứng khi di chuột vào nút menu */
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #e3f2fd;
        color: #0d47a1;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateX(5px); /* Nút trượt nhẹ sang phải */
    }
    
    /* Nút đang được chọn (Active) - Giả lập bằng viền màu */
    [data-testid="stSidebar"] .stButton > button:focus {
        border-left: 5px solid #0d47a1;
        background-color: #e3f2fd;
    }

    /* 2. STYLE CHO CARD BÁO CÁO (DASHBOARD) */
    .metric-container {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 20px;
    }
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        flex: 1;
        text-align: center;
        border-top: 4px solid #2196F3;
    }
    .metric-val { font-size: 28px; font-weight: bold; color: #333; }
    .metric-lbl { font-size: 14px; color: #666; text-transform: uppercase; letter-spacing: 1px; }

    /* 3. STYLE CHO TABLE & KHÁC */
    .social-btn {
        display: inline-block; padding: 3px 8px; border-radius: 4px; color: white !important;
        text-decoration: none; font-size: 11px; margin-right: 4px; font-weight: bold;
    }
    .zalo {background-color: #0068FF;} .fb {background-color: #1877F2;} .tiktok {background-color: #000000;}
    </style>
""", unsafe_allow_html=True)

# --- KẾT NỐI API ---
@st.cache_resource
def get_gcp_service():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        service_drive = build('drive', 'v3', credentials=creds)
        return client, service_drive
    except: return None, None

client, drive_service = get_gcp_service()
if not client: st.error("⚠️ Lỗi kết nối!"); st.stop()
try:
    sheet_ungvien = client.open("TuyenDungKCN_Data").worksheet("UngVien")
    sheet_users = client.open("TuyenDungKCN_Data").worksheet("Users")
except: st.error("⚠️ Không tìm thấy Sheet!"); st.stop()

# --- HELPER FUNCTIONS ---
def upload_to_drive(file_obj, file_name):
    try:
        metadata = {'name': file_name, 'parents': [FOLDER_ID_DRIVE]}
        media = MediaIoBaseUpload(file_obj, mimetype=file_obj.type)
        file = drive_service.files().create(body=metadata, media_body=media, fields='webContentLink').execute()
        return file.get('webContentLink')
    except: return None

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO(); img.save(buf)
    return buf.getvalue()

# --- SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_page' not in st.session_state: st.session_state.current_page = "dashboard"

def set_page(page_name):
    st.session_state.current_page = page_name

# --- LOGIN SCREEN ---
def login_screen():
    st.markdown("<br><h1 style='text-align: center; color:#0d47a1'>🔐 HR ADMIN SYSTEM</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        with st.form("login", clear_on_submit=False):
            u = st.text_input("Tên đăng nhập")
            p = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("ĐĂNG NHẬP", use_container_width=True):
                users = sheet_users.get_all_records()
                for user in users:
                    if str(user['Username']) == u and str(user['Password']) == p:
                        st.session_state.logged_in = True
                        st.session_state.user_role = user['Role']
                        st.session_state.user_name = user['HoTen']
                        st.rerun()
                st.error("Sai thông tin!")

# --- MAIN APPLICATION ---
def main_app():
    # Load data
    df = pd.DataFrame(sheet_ungvien.get_all_records())

    # --- MENU BÊN TRÁI (DẠNG KHỐI) ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"Vai trò: {st.session_state.user_role.upper()}")
        st.markdown("---")
        
        # Các nút Menu dạng Block (Nhờ CSS ở trên)
        if st.button("🏠 TỔNG QUAN DASHBOARD"): set_page("dashboard")
        if st.button("📝 NHẬP HỒ SƠ ỨNG VIÊN"): set_page("input")
        if st.button("📋 DANH SÁCH & TRA CỨU"): set_page("list")
        if st.button("🖩 CÔNG CỤ TÍNH LƯƠNG"): set_page("salary")
        
        if st.session_state.user_role == "admin":
            st.markdown("---")
            if st.button("⚙️ QUẢN TRỊ HỆ THỐNG"): set_page("admin")
            
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất"): st.session_state.logged_in = False; st.rerun()

    # --- TRANG 1: DASHBOARD BÁO CÁO KHOA HỌC ---
    if st.session_state.current_page == "dashboard":
        st.title("📊 Bảng Điều Khiển Trung Tâm")
        st.markdown(f"Cập nhật lúc: {datetime.now().strftime('%H:%M %d/%m/%Y')}")
        
        if not df.empty:
            # 1. METRIC CARDS (THẺ SỐ LIỆU) - Giao diện ngang
            st.markdown("""
            <div class="metric-container">
                <div class="metric-card" style="border-top-color: #2196F3;">
                    <div class="metric-val">{}</div>
                    <div class="metric-lbl">Tổng Hồ Sơ</div>
                </div>
                <div class="metric-card" style="border-top-color: #4CAF50;">
                    <div class="metric-val">{}</div>
                    <div class="metric-lbl">Đã Đi Làm</div>
                </div>
                <div class="metric-card" style="border-top-color: #FF9800;">
                    <div class="metric-val">{}</div>
                    <div class="metric-lbl">Chờ Phỏng Vấn</div>
                </div>
                <div class="metric-card" style="border-top-color: #E91E63;">
                    <div class="metric-val">{}</div>
                    <div class="metric-lbl">Nguồn MXH</div>
                </div>
            </div>
            """.format(
                len(df),
                len(df[df['TrangThai'] == 'Đã đi làm']),
                len(df[df['TrangThai'] == 'Mới nhận']),
                len(df[df['Nguồn'].isin(['Facebook', 'TikTok', 'Zalo'])])
            ), unsafe_allow_html=True)
            
            # 2. BIỂU ĐỒ (CHARTS)
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("📈 Hiệu Suất Tuyển Dụng (KPI)")
                if 'NguoiTuyen' in df.columns:
                    kpi = df['NguoiTuyen'].value_counts()
                    st.bar_chart(kpi, color="#2196F3")
                else: st.warning("Chưa có dữ liệu KPI")
            
            with c2:
                st.subheader("🍰 Nguồn Ứng Viên")
                st.write("Tỷ lệ các kênh tuyển dụng:")
                source_counts = df['Nguồn'].value_counts()
                st.dataframe(source_counts, use_container_width=True)

    # --- TRANG 2: NHẬP LIỆU ---
    elif st.session_state.current_page == "input":
        st.header("📝 Nhập Hồ Sơ Mới")
        with st.container(border=True):
            with st.form("input_form"):
                col_img, col_info = st.columns([1, 3])
                with col_img:
                    uploaded_file = st.file_uploader("Ảnh", type=['jpg','png'])
                    if uploaded_file: st.image(uploaded_file, width=150)
                
                with col_info:
                    c1, c2 = st.columns(2)
                    name = c1.text_input("Họ tên (*)")
                    phone = c2.text_input("SĐT (*)")
                    cccd = st.text_input("Số CCCD/CMND (*)")
                
                st.markdown("---")
                r1, r2, r3 = st.columns(3)
                yob = r1.number_input("Năm sinh", 1980, 2010, 2000)
                pos = r2.selectbox("Vị trí", ["Công nhân", "Kỹ thuật", "Kho", "Bảo vệ"])
                source = r3.selectbox("Nguồn", ["Facebook", "Zalo", "Trực tiếp", "Giới thiệu"])
                
                r4, r5, r6 = st.columns(3)
                bus = r4.selectbox("Xe tuyến", ["Tự túc", "Tuyến A", "Tuyến B"])
                doc = r5.selectbox("Giấy tờ", ["Chưa có", "Đủ giấy tờ", "Thiếu khám SK"])
                fb = r6.text_input("Link Facebook")
                
                if st.form_submit_button("LƯU HỒ SƠ NGAY", type="primary"):
                    if name and phone and cccd:
                         # Logic lưu (như cũ)
                         link = upload_to_drive(uploaded_file, f"{name}.jpg") if uploaded_file else ""
                         row = [datetime.now().strftime("%d/%m/%Y"), name.upper(), yob, "", f"'{phone}", f"'{cccd}", pos, "Mới nhận", "", source, link, bus, "No", st.session_state.user_name, fb, "", doc]
                         sheet_ungvien.append_row(row)
                         st.success("✅ Lưu thành công!")
                         time.sleep(1); st.rerun()
                    else: st.error("Thiếu thông tin bắt buộc!")

    # --- TRANG 3: DANH SÁCH ---
    elif st.session_state.current_page == "list":
        st.header("📋 Danh Sách & Tìm Kiếm")
        
        # Thanh tìm kiếm to rõ
        search_query = st.text_input("🔍 Nhập Tên, SĐT hoặc CCCD để tìm kiếm...", placeholder="Ví dụ: 0988...")
        
        if not df.empty:
            filtered_df = df
            if search_query:
                filtered_df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
            
            # Hiển thị bảng tóm tắt
            st.dataframe(filtered_df[['HoTen', 'NamSinh', 'SDT', 'ViTri', 'TrangThai']], use_container_width=True, hide_index=True)
            
            # Hiển thị chi tiết dạng thẻ bên dưới
            st.markdown("### Chi tiết hồ sơ:")
            for i, row in filtered_df.iterrows():
                with st.expander(f"📌 {row['HoTen']} - {row['ViTri']}"):
                    ec1, ec2, ec3 = st.columns([1, 2, 1])
                    with ec1:
                        if row.get('LinkAnh'): st.image(row['LinkAnh'], width=120)
                        qr_code = generate_qr(f"{row['HoTen']}|{row['SDT']}|{row.get('CCCD')}")
                        st.image(qr_code, width=80, caption="Mã hồ sơ")
                    with ec2:
                        st.write(f"📞 **SĐT:** {row['SDT']}")
                        st.write(f"🆔 **CCCD:** {row.get('CCCD')}")
                        st.write(f"📂 **Giấy tờ:** {row.get('TrangThaiHoSo')}")
                        if row.get('LinkFB'): st.markdown(f"🌐 [Facebook Profile]({row['LinkFB']})")
                    with ec3:
                         st.info(f"Nguồn: {row['Nguồn']}")
                         st.write(f"Người nhập: {row.get('NguoiTuyen')}")

    # --- TRANG 4: TÍNH LƯƠNG ---
    elif st.session_state.current_page == "salary":
        st.header("🖩 Ước Tính Lương")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            lcb = col1.number_input("Lương cơ bản", value=4500000, step=100000)
            pc = col1.number_input("Phụ cấp", value=1000000, step=50000)
            ot = col2.number_input("Giờ tăng ca (giờ)", value=40)
            hs = col2.number_input("Hệ số", value=1.5)
            
            total = lcb + pc + ((lcb/26/8)*ot*hs)
            st.markdown(f"<h2 style='text-align:center; color:#2E7D32'>💰 Tổng: {int(total):,} VNĐ</h2>", unsafe_allow_html=True)

    # --- TRANG 5: ADMIN ---
    elif st.session_state.current_page == "admin":
        st.header("⚙️ Quản Trị Hệ Thống")
        users = sheet_users.get_all_records()
        st.dataframe(users, use_container_width=True)
        with st.form("admin_role"):
            st.write("Sửa quyền nhân viên:")
            u = st.selectbox("Username", [x['Username'] for x in users])
            r = st.selectbox("Quyền mới", ["staff", "admin"])
            if st.form_submit_button("Cập nhật"):
                cell = sheet_users.find(u)
                sheet_users.update_cell(cell.row, 3, r)
                st.success("Đã cập nhật!"); time.sleep(1); st.rerun()

# --- CHẠY APP ---
if st.session_state.logged_in:
    main_app()
else:
    login_screen()
