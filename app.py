import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from datetime import datetime
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="HR Mobile Pro", layout="wide", page_icon="📱")

# --- CẤU HÌNH ID THƯ MỤC DRIVE (ĐÃ CẬP NHẬT CỦA BẠN) ---
FOLDER_ID_DRIVE = "1Sw91t5o-m8fwZsbGpJw8Yex_WzV8etCx" 

# --- CSS BIẾN GIAO DIỆN THÀNH IPHONE STYLE ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 100px;
        border-radius: 20px;
        font-size: 20px;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.2);
    }
    .app-icon {font-size: 40px; display: block; margin-bottom: 10px;}
    .profile-pic {border-radius: 50%; width: 100px; height: 100px; object-fit: cover;}
    </style>
""", unsafe_allow_html=True)

# --- KẾT NỐI GOOGLE APIS ---
@st.cache_resource
def get_gcp_service():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds", 
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        
        # Client cho Sheet
        client_sheet = gspread.authorize(creds)
        
        # Client cho Drive (Upload ảnh)
        service_drive = build('drive', 'v3', credentials=creds)
        
        return client_sheet, service_drive
    except Exception as e:
        return None, None

client, drive_service = get_gcp_service()

# Kiểm tra kết nối
if client is None or drive_service is None:
    st.error("⚠️ Lỗi kết nối Google API! Hãy kiểm tra lại Secrets hoặc file JSON.")
    st.stop()

try:
    # Mở sheet theo tên Tab mới
    sheet_ungvien = client.open("TuyenDungKCN_Data").worksheet("UngVien")
    sheet_users = client.open("TuyenDungKCN_Data").worksheet("Users")
except Exception as e:
    st.error("⚠️ Lỗi không tìm thấy Tab! Hãy chắc chắn file Google Sheet của bạn đã có tab tên là 'UngVien' và 'Users'.")
    st.stop()

# --- HÀM HỖ TRỢ UPLOAD ẢNH ---
def upload_to_drive(file_obj, file_name):
    try:
        file_metadata = {'name': file_name, 'parents': [FOLDER_ID_DRIVE]}
        media = MediaIoBaseUpload(file_obj, mimetype=file_obj.type)
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webContentLink').execute()
        return file.get('webContentLink') # Trả về link ảnh
    except Exception as e:
        st.error(f"Lỗi upload ảnh: {e}")
        return None

# --- QUẢN LÝ SESSION (TRẠNG THÁI ĐĂNG NHẬP) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Home"

# --- MÀN HÌNH ĐĂNG NHẬP ---
def login_screen():
    st.markdown("<h1 style='text-align: center;'>🔐 ĐĂNG NHẬP HỆ THỐNG</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submitted = st.form_submit_button("Đăng Nhập")
            
            if submitted:
                try:
                    users = sheet_users.get_all_records()
                    found = False
                    for user in users:
                        if str(user['Username']) == username and str(user['Password']) == password:
                            st.session_state.logged_in = True
                            st.session_state.user_role = user['Role']
                            st.session_state.user_name = user['HoTen']
                            found = True
                            st.success("Đăng nhập thành công!")
                            time.sleep(0.5)
                            st.rerun()
                    if not found:
                        st.error("Sai tên đăng nhập hoặc mật khẩu!")
                except Exception as e:
                     st.error("Lỗi đọc dữ liệu Users. Hãy kiểm tra lại file Sheet!")

# --- MÀN HÌNH CHÍNH (IPHONE STYLE) ---
def home_screen():
    st.markdown(f"### 👋 Xin chào, {st.session_state.user_name} ({st.session_state.user_role})")
    if st.button("🚪 Đăng xuất"):
        st.session_state.logged_in = False
        st.rerun()
        
    st.markdown("---")
    
    # Giao diện lưới 2 cột
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="app-icon">➕</div>', unsafe_allow_html=True)
        if st.button("NHẬP HỒ SƠ"):
            st.session_state.current_page = "Input"
            st.rerun()
            
        st.markdown('<div class="app-icon">📊</div>', unsafe_allow_html=True)
        if st.button("BÁO CÁO"):
            st.session_state.current_page = "Report"
            st.rerun()

    with col2:
        st.markdown('<div class="app-icon">📋</div>', unsafe_allow_html=True)
        if st.button("DANH SÁCH"):
            st.session_state.current_page = "List"
            st.rerun()

        # Chỉ Admin mới thấy nút quản lý nhân viên
        if st.session_state.user_role == "admin":
            st.markdown('<div class="app-icon">⚙️</div>', unsafe_allow_html=True)
            if st.button("QUẢN TRỊ VIÊN"):
                st.session_state.current_page = "Admin"
                st.rerun()
        else:
            st.markdown('<div class="app-icon">🔒</div>', unsafe_allow_html=True)
            st.info("Menu Admin")

# --- TRANG NHẬP HỒ SƠ (CÓ ẢNH) ---
def input_page():
    if st.button("⬅️ Quay về"):
        st.session_state.current_page = "Home"
        st.rerun()
        
    st.header("📝 Thêm Ứng Viên Mới")
    
    with st.form("add_candidate"):
        c1, c2 = st.columns([1, 2])
        with c1:
            # Upload ảnh
            uploaded_file = st.file_uploader("Ảnh chân dung", type=['png', 'jpg', 'jpeg'])
            if uploaded_file:
                st.image(uploaded_file, width=150, caption="Preview")
        
        with c2:
            name = st.text_input("Họ tên (*)")
            phone = st.text_input("Số điện thoại (*)")
            yob = st.number_input("Năm sinh", 1980, 2010, 2000)
            
        pos = st.selectbox("Vị trí", ["Công nhân", "Kỹ thuật", "Bảo vệ", "Tạp vụ", "Khác"])
        source = st.selectbox("Nguồn", ["Facebook", "Zalo", "Giới thiệu", "Trực tiếp"])
        note = st.text_area("Ghi chú")
        
        btn = st.form_submit_button("Lưu Hồ Sơ")
        
        if btn:
            if not name or not phone:
                st.error("Thiếu tên hoặc SĐT!")
            else:
                with st.spinner("Đang xử lý ảnh và dữ liệu..."):
                    image_link = ""
                    if uploaded_file:
                        # Upload lên Drive
                        file_name = f"{name}_{phone}_{datetime.now().strftime('%Y%m%d')}.jpg"
                        image_link = upload_to_drive(uploaded_file, file_name)

                    # Lưu vào Sheet
                    row = [
                        datetime.now().strftime("%d/%m/%Y"),
                        name, yob, "", f"'{phone}", pos, "Mới nhận", note, source, image_link
                    ]
                    sheet_ungvien.append_row(row)
                    st.success("✅ Đã lưu thành công!")
                    time.sleep(1)
                    st.rerun()

# --- TRANG DANH SÁCH (CÓ HIỆN ẢNH) ---
def list_page():
    if st.button("⬅️ Quay về"):
        st.session_state.current_page = "Home"
        st.rerun()
        
    st.header("📋 Danh Sách Hồ Sơ")
    data = sheet_ungvien.get_all_records()
    df = pd.DataFrame(data)
    
    if not df.empty:
        search = st.text_input("Tìm kiếm (Tên/SĐT)...")
        if search:
            df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        
        # Hiển thị dạng Card đẹp thay vì bảng
        for i, row in df.iterrows():
            with st.expander(f"{row['HoTen']} - {row['ViTri']}"):
                c_img, c_info = st.columns([1, 3])
                with c_img:
                    if row.get('LinkAnh'):
                        st.image(row['LinkAnh'], width=100)
                    else:
                        st.write("📷 Không có ảnh")
                with c_info:
                    st.write(f"📞 **SĐT:** {row['SDT']}")
                    st.write(f"🏷️ **Trạng thái:** {row['TrangThai']}")
                    st.write(f"ℹ️ **Nguồn:** {row.get('Nguồn', '')}")
                    if row.get('GhiChu'):
                         st.info(f"Note: {row['GhiChu']}")

# --- TRANG QUẢN LÝ USER (CHỈ ADMIN) ---
def admin_page():
    if st.button("⬅️ Quay về"):
        st.session_state.current_page = "Home"
        st.rerun()
    
    st.header("⚙️ Quản Lý Tài Khoản Nhân Viên")
    
    # Tạo user mới
    with st.form("new_user"):
        st.write("Tạo tài khoản mới:")
        c1, c2 = st.columns(2)
        with c1:
            u_user = st.text_input("Username (Tên đăng nhập)")
            u_name = st.text_input("Tên nhân viên")
        with c2:
            u_pass = st.text_input("Password (Mật khẩu)")
            u_role = st.selectbox("Phân quyền", ["staff", "admin"])
            
        if st.form_submit_button("Thêm nhân viên"):
            if u_user and u_pass:
                sheet_users.append_row([u_user, u_pass, u_role, u_name])
                st.success("Đã thêm thành công!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Vui lòng điền đủ thông tin")

    # Xem danh sách user
    st.subheader("Danh sách hiện tại:")
    users = sheet_users.get_all_records()
    st.dataframe(pd.DataFrame(users))

# --- LOGIC ĐIỀU HƯỚNG CHÍNH ---
if not st.session_state.logged_in:
    login_screen()
else:
    if st.session_state.current_page == "Home":
        home_screen()
    elif st.session_state.current_page == "Input":
        input_page()
    elif st.session_state.current_page == "List":
        list_page()
    elif st.session_state.current_page == "Report":
        st.title("📊 Báo cáo")
        st.info("Tính năng đang được cập nhật thêm biểu đồ...")
        if st.button("⬅️ Quay về"):
            st.session_state.current_page = "Home"
            st.rerun()
    elif st.session_state.current_page == "Admin":
        admin_page()
