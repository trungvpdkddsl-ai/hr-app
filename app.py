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
st.set_page_config(page_title="HR Pro Dashboard", layout="wide", page_icon="💠")

# --- CẤU HÌNH ID DRIVE (GIỮ NGUYÊN) ---
FOLDER_ID_DRIVE = "1Sw91t5o-m8fwZsbGpJw8Yex_WzV8etCx"

# --- CSS TÙY BIẾN GIAO DIỆN Ô VUÔNG ---
st.markdown("""
    <style>
    /* Ẩn menu mặc định của Streamlit cho gọn */
    #MainMenu {visibility: hidden;}
    
    /* Style cho các nút Dashboard (Ô vuông) */
    div.stButton > button:first-child {
        height: 120px;
        width: 100%;
        border-radius: 15px;
        border: none;
        background-color: #f8f9fa;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        color: #333;
        font-size: 20px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #e3f2fd;
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        color: #0d47a1;
        border: 2px solid #0d47a1;
    }
    
    /* Style cho Card thống kê */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2196F3;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-value {font-size: 32px; font-weight: bold; color: #1565c0;}
    .metric-label {font-size: 14px; color: #666; text-transform: uppercase;}
    
    /* Nút Social nhỏ */
    .social-btn {
        display: inline-block; padding: 4px 10px; border-radius: 4px; color: white !important;
        text-decoration: none; font-size: 11px; margin-right: 4px; font-weight: bold;
    }
    .zalo {background-color: #0068FF;} .fb {background-color: #1877F2;} .tiktok {background-color: #000000;}
    </style>
""", unsafe_allow_html=True)

# --- KẾT NỐI GOOGLE APIS ---
@st.cache_resource
def get_gcp_service():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        service_drive = build('drive', 'v3', credentials=creds)
        return client, service_drive
    except:
        return None, None

client, drive_service = get_gcp_service()

if not client:
    st.error("⚠️ Lỗi kết nối! Kiểm tra lại file Secrets.")
    st.stop()

try:
    sheet_ungvien = client.open("TuyenDungKCN_Data").worksheet("UngVien")
    sheet_users = client.open("TuyenDungKCN_Data").worksheet("Users")
except:
    st.error("⚠️ Không tìm thấy Sheet!")
    st.stop()

# --- HÀM HỖ TRỢ ---
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

def check_blacklist(cccd, df):
    if df.empty: return False
    return str(cccd) in df[df['TrangThai'] == "Vĩnh viễn không tuyển"]['CCCD'].astype(str).values

# --- QUẢN LÝ ĐIỀU HƯỚNG ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_page' not in st.session_state: st.session_state.current_page = "dashboard"

def navigate_to(page):
    st.session_state.current_page = page
    st.rerun()

# --- LOGIN SCREEN ---
def login_screen():
    st.markdown("<br><br><h1 style='text-align: center;'>💠 HR MANAGEMENT SYSTEM</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("ĐĂNG NHẬP", use_container_width=True):
                users = sheet_users.get_all_records()
                for user in users:
                    if str(user['Username']) == u and str(user['Password']) == p:
                        st.session_state.logged_in = True
                        st.session_state.user_role = user['Role']
                        st.session_state.user_name = user['HoTen']
                        st.rerun()
                st.error("Sai thông tin!")

# --- GIAO DIỆN CHÍNH ---
def main_app():
    # Load dữ liệu
    df = pd.DataFrame(sheet_ungvien.get_all_records())

    # --- SIDEBAR (CHỈ CHỨA INFO VÀ NÚT HOME) ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
        st.markdown(f"### 👋 {st.session_state.user_name}")
        st.markdown(f"Vai trò: **{st.session_state.user_role.upper()}**")
        
        st.markdown("---")
        if st.button("🏠 TRANG CHỦ (MENU)", use_container_width=True):
            navigate_to("dashboard")
        
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # --- TRANG 1: DASHBOARD (MENU Ô VUÔNG) ---
    if st.session_state.current_page == "dashboard":
        st.title("🎛️ Bảng Điều Khiển Trung Tâm")
        st.markdown("Chọn chức năng bên dưới:")
        
        # Hàng 1
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📝\nNHẬP HỒ SƠ", use_container_width=True): navigate_to("input")
        with c2:
            if st.button("📋\nDANH SÁCH & SOCIAL", use_container_width=True): navigate_to("list")
        with c3:
            if st.button("📊\nBÁO CÁO & KPI", use_container_width=True): navigate_to("report")
            
        # Hàng 2
        c4, c5, c6 = st.columns(3)
        with c4:
            if st.button("🖩\nTÍNH LƯƠNG NHANH", use_container_width=True): navigate_to("salary")
        with c5:
            # Chỉ Admin mới bấm được nút này
            if st.session_state.user_role == "admin":
                if st.button("⚙️\nQUẢN TRỊ ADMIN", use_container_width=True): navigate_to("admin")
            else:
                st.button("🔒\nADMIN (KHÓA)", disabled=True, use_container_width=True)
        with c6:
             st.info(f"📅 Hôm nay: {datetime.now().strftime('%d/%m/%Y')}")

        # Thống kê nhanh bên dưới
        st.markdown("---")
        if not df.empty:
            st.subheader("Tiến độ hôm nay")
            today = datetime.now().strftime("%d/%m/%Y")
            today_count = len(df[df['NgayNhap'].astype(str).str.contains(today)])
            st.progress(min(today_count / 10, 1.0))
            st.caption(f"Đã nhập {today_count} hồ sơ hôm nay (Mục tiêu: 10)")

    # --- TRANG 2: NHẬP HỒ SƠ ---
    elif st.session_state.current_page == "input":
        st.header("📝 Nhập Hồ Sơ Ứng Viên")
        with st.form("full_input"):
            c1, c2 = st.columns([1, 2])
            with c1:
                uploaded_file = st.file_uploader("Ảnh 3x4", type=['jpg','png'])
                if uploaded_file: st.image(uploaded_file, width=120)
            with c2:
                name = st.text_input("Họ tên (*)")
                phone = st.text_input("SĐT (*)")
                cccd = st.text_input("CCCD (*)")
            
            c3, c4 = st.columns(2)
            yob = c3.number_input("Năm sinh", 1980, 2010, 2000)
            hometown = c4.text_input("Quê quán")
            pos = st.selectbox("Vị trí", ["Công nhân", "Kỹ thuật", "Kho", "Bảo vệ", "Tạp vụ"])
            
            st.markdown("---")
            st.write("Thông tin bổ sung:")
            r1, r2, r3 = st.columns(3)
            bus = r1.selectbox("Xe tuyến", ["Tự túc", "Tuyến A", "Tuyến B"])
            source = r2.selectbox("Nguồn", ["Facebook", "Zalo", "Trực tiếp", "Giới thiệu"])
            doc = r3.selectbox("Giấy tờ", ["Chưa có", "Đủ giấy tờ", "Thiếu khám SK"])
            
            fb = st.text_input("Link Facebook")
            
            if st.form_submit_button("💾 LƯU HỒ SƠ", type="primary"):
                if not name or not phone or not cccd:
                    st.error("Thiếu Tên, SĐT hoặc CCCD!")
                elif not df.empty and str(cccd) in df['CCCD'].astype(str).values:
                    st.warning("⚠️ Trùng CCCD!")
                else:
                    with st.spinner("Đang lưu..."):
                        link = upload_to_drive(uploaded_file, f"{name}.jpg") if uploaded_file else ""
                        row = [datetime.now().strftime("%d/%m/%Y"), name.upper(), yob, hometown, f"'{phone}", f"'{cccd}", pos, "Mới nhận", "", source, link, bus, "Không", st.session_state.user_name, fb, "", doc]
                        sheet_ungvien.append_row(row)
                        st.success("✅ Đã lưu!"); time.sleep(1); navigate_to("input")

    # --- TRANG 3: BÁO CÁO (KHOA HỌC) ---
    elif st.session_state.current_page == "report":
        st.header("📊 Báo Cáo & Phân Tích")
        
        if df.empty: st.info("Chưa có dữ liệu."); return
        
        # 1. Thẻ chỉ số (Metric Cards)
        st.subheader("1. Tổng quan")
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f'<div class="metric-card"><div class="metric-value">{len(df)}</div><div class="metric-label">Tổng hồ sơ</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card"><div class="metric-value">{len(df[df["TrangThai"]=="Đã đi làm"])}</div><div class="metric-label">Đã đi làm</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card"><div class="metric-value">{len(df[df["TrangThaiHoSo"]=="Đủ giấy tờ"])}</div><div class="metric-label">Đủ hồ sơ gốc</div></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="metric-card"><div class="metric-value">{len(df[df["Nguon"]=="Facebook"])}</div><div class="metric-label">Từ Facebook</div></div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 2. Phân tích sâu (Chia tab)
        tab1, tab2 = st.tabs(["🏆 KPI Nhân Viên (Leaderboard)", "📈 Biểu Đồ Phễu"])
        
        with tab1:
            st.markdown("### Bảng xếp hạng tuyển dụng tháng này")
            if 'NguoiTuyen' in df.columns:
                kpi_df = df['NguoiTuyen'].value_counts().reset_index()
                kpi_df.columns = ['Nhân viên', 'Số lượng']
                st.dataframe(kpi_df, use_container_width=True, hide_index=True)
                st.bar_chart(kpi_df.set_index('Nhân viên'))
            else:
                st.warning("Thiếu cột dữ liệu Người Tuyển.")
                
        with tab2:
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Tỷ lệ chuyển đổi theo Vị trí**")
                st.bar_chart(df['ViTri'].value_counts())
            with c2:
                st.write("**Nguồn ứng viên hiệu quả nhất**")
                st.bar_chart(df['Nguồn'].value_counts())

    # --- TRANG 4: DANH SÁCH ---
    elif st.session_state.current_page == "list":
        st.header("📋 Tra Cứu Hồ Sơ")
        search = st.text_input("🔍 Tìm kiếm nhanh (Tên/SĐT/CCCD)")
        if not df.empty:
            if search: df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            st.dataframe(df[['HoTen', 'SDT', 'ViTri', 'TrangThai', 'Nguồn']], use_container_width=True, hide_index=True)
            
            with st.expander("Xem chi tiết & Mã QR"):
                for i, row in df.iterrows():
                    st.markdown(f"**{row['HoTen']}** - {row['SDT']}")
                    st.image(generate_qr(f"{row['HoTen']}-{row['CCCD']}"), width=80)
                    st.markdown("---")

    # --- TRANG 5: TÍNH LƯƠNG ---
    elif st.session_state.current_page == "salary":
        st.header("🖩 Tính Lương Nhanh")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            lcb = col1.number_input("Lương cơ bản", 4500000)
            pc = col1.number_input("Phụ cấp", 1000000)
            ot = col2.number_input("Giờ OT", 40)
            st.metric("Tổng Thực Nhận Dự Kiến", f"{int(lcb + pc + (lcb/208*ot*1.5)):,} VNĐ")

    # --- TRANG 6: ADMIN ---
    elif st.session_state.current_page == "admin":
        st.header("⚙️ Quản Trị Hệ Thống")
        users = sheet_users.get_all_records()
        st.dataframe(users)
        with st.form("edit_role"):
            u = st.selectbox("Chọn User", [u['Username'] for u in users])
            r = st.selectbox("Quyền mới", ["staff", "admin"])
            if st.form_submit_button("Cập nhật"):
                cell = sheet_users.find(u)
                sheet_users.update_cell(cell.row, 3, r)
                st.success("Xong!")

# --- RUN ---
if st.session_state.logged_in:
    main_app()
else:
    login_screen()
