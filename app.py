import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import time
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="HR Mobile Pro", layout="wide", page_icon="📱")

# --- CẤU HÌNH ID THƯ MỤC DRIVE ---
# Thay mã ID thư mục Drive thật của bạn vào đây
FOLDER_ID_DRIVE = "1Sw91t5o-m8fwZsbGpJw8Yex_WzV8etCx" 

# --- CSS GIAO DIỆN (IPHONE STYLE) ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 60px;
        border-radius: 15px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
    }
    .big-btn {height: 100px !important; font-size: 20px !important;}
    .app-icon {font-size: 40px; display: block; margin-bottom: 10px;}
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
    except Exception as e:
        return None, None

client, drive_service = get_gcp_service()

# Kiểm tra kết nối
if not client or not drive_service:
    st.error("⚠️ Lỗi kết nối Google API! Kiểm tra lại file secrets hoặc requirements.txt")
    st.stop()

try:
    sheet_ungvien = client.open("TuyenDungKCN_Data").worksheet("UngVien")
    sheet_users = client.open("TuyenDungKCN_Data").worksheet("Users")
except:
    st.error("⚠️ Lỗi: Không tìm thấy Sheet! Hãy đảm bảo file Google Sheet có tab 'UngVien' và 'Users'.")
    st.stop()

# --- HÀM HỖ TRỢ ---
def upload_to_drive(file_obj, file_name):
    try:
        metadata = {'name': file_name, 'parents': [FOLDER_ID_DRIVE]}
        media = MediaIoBaseUpload(file_obj, mimetype=file_obj.type)
        file = drive_service.files().create(body=metadata, media_body=media, fields='webContentLink').execute()
        return file.get('webContentLink')
    except:
        return None

# --- QUẢN LÝ SESSION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Home"

# ==========================================
# 1. MÀN HÌNH ĐĂNG NHẬP & ĐĂNG KÝ
# ==========================================
def login_screen():
    st.markdown("<h1 style='text-align: center;'>🔐 CỔNG THÔNG TIN HR</h1>", unsafe_allow_html=True)
    
    col_center = st.columns([1, 2, 1])
    with col_center[1]:
        tab1, tab2 = st.tabs(["🔑 ĐĂNG NHẬP", "📝 ĐĂNG KÝ MỚI"])
        
        # --- TAB ĐĂNG NHẬP ---
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Tên đăng nhập")
                password = st.text_input("Mật khẩu", type="password")
                btn_login = st.form_submit_button("Đăng Nhập Ngay")
                
                if btn_login:
                    try:
                        users = sheet_users.get_all_records()
                        found = False
                        for user in users:
                            # Lưu ý: So sánh chuỗi để tránh lỗi kiểu dữ liệu
                            if str(user['Username']).strip() == username.strip() and str(user['Password']).strip() == password.strip():
                                st.session_state.logged_in = True
                                st.session_state.user_role = user['Role']
                                st.session_state.user_name = user['HoTen']
                                found = True
                                st.success(f"Chào mừng {user['HoTen']}!")
                                time.sleep(0.5)
                                st.rerun()
                        if not found:
                            st.error("Sai tài khoản hoặc mật khẩu!")
                    except Exception as e:
                        st.error(f"Lỗi hệ thống: {e}")

        # --- TAB ĐĂNG KÝ ---
        with tab2:
            st.info("Tài khoản mới sẽ có quyền mặc định là 'Nhân viên'.")
            with st.form("register_form"):
                new_user = st.text_input("Tên đăng nhập mới (*)")
                new_pass = st.text_input("Mật khẩu (*)", type="password")
                new_name = st.text_input("Họ và tên của bạn (*)")
                btn_register = st.form_submit_button("Đăng Ký Tài Khoản")
                
                if btn_register:
                    if new_user and new_pass and new_name:
                        # Kiểm tra trùng tên đăng nhập
                        existing_users = sheet_users.col_values(1) # Lấy cột Username
                        if new_user in existing_users:
                            st.warning("Tên đăng nhập này đã tồn tại! Vui lòng chọn tên khác.")
                        else:
                            # Mặc định role là 'staff'
                            sheet_users.append_row([new_user, new_pass, "staff", new_name])
                            st.success("✅ Đăng ký thành công! Hãy quay lại tab Đăng Nhập.")
                    else:
                        st.error("Vui lòng điền đầy đủ thông tin!")

# ==========================================
# 2. MÀN HÌNH CHÍNH (DASHBOARD)
# ==========================================
def home_screen():
    st.markdown(f"### 👋 Xin chào, **{st.session_state.user_name}**")
    
    # Hiển thị vai trò (Role badge)
    role_color = "red" if st.session_state.user_role == "admin" else "blue"
    st.markdown(f"Quyền hạn: <span style='color:{role_color}; font-weight:bold; border:1px solid {role_color}; padding:2px 5px; border-radius:5px'>{st.session_state.user_role.upper()}</span>", unsafe_allow_html=True)

    if st.button("🚪 Đăng xuất", key="logout"):
        st.session_state.logged_in = False
        st.rerun()
        
    st.markdown("---")
    
    # Menu dạng lưới
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="app-icon">➕</div>', unsafe_allow_html=True)
        if st.button("NHẬP HỒ SƠ", key="btn_input"):
            st.session_state.current_page = "Input"
            st.rerun()
            
        st.markdown('<div class="app-icon">📊</div>', unsafe_allow_html=True)
        if st.button("BÁO CÁO", key="btn_report"):
            st.session_state.current_page = "Report"
            st.rerun()

    with c2:
        st.markdown('<div class="app-icon">📋</div>', unsafe_allow_html=True)
        if st.button("DANH SÁCH", key="btn_list"):
            st.session_state.current_page = "List"
            st.rerun()

        # Nút Admin chỉ hiện với Admin/Manager
        if st.session_state.user_role in ["admin", "manager"]:
            st.markdown('<div class="app-icon">⚙️</div>', unsafe_allow_html=True)
            if st.button("QUẢN TRỊ", key="btn_admin"):
                st.session_state.current_page = "Admin"
                st.rerun()
        else:
            st.markdown('<div class="app-icon">🔒</div>', unsafe_allow_html=True)
            st.button("Admin (Khóa)", disabled=True)

# ==========================================
# 3. CÁC TRANG CHỨC NĂNG
# ==========================================

def input_page():
    if st.button("⬅️ Quay về"): st.session_state.current_page = "Home"; st.rerun()
    st.header("📝 Nhập Hồ Sơ Ứng Viên")
    
    with st.form("add_candidate"):
        c1, c2 = st.columns([1, 2])
        with c1:
            uploaded_file = st.file_uploader("Ảnh chân dung", type=['png', 'jpg', 'jpeg'])
            if uploaded_file: st.image(uploaded_file, width=150)
        with c2:
            name = st.text_input("Họ tên (*)")
            phone = st.text_input("Số điện thoại (*)")
            yob = st.number_input("Năm sinh", 1980, 2010, 2000)
            
        c3, c4 = st.columns(2)
        pos = c3.selectbox("Vị trí", ["Công nhân", "Kỹ thuật", "Bảo vệ", "Tạp vụ", "Khác"])
        source = c4.selectbox("Nguồn", ["Facebook", "Zalo", "Giới thiệu", "Trực tiếp"])
        note = st.text_area("Ghi chú")
        
        if st.form_submit_button("Lưu Hồ Sơ"):
            if not name or not phone:
                st.error("Thiếu tên hoặc SĐT!")
            else:
                with st.spinner("Đang lưu..."):
                    link = upload_to_drive(uploaded_file, f"{name}_{phone}.jpg") if uploaded_file else ""
                    sheet_ungvien.append_row([
                        datetime.now().strftime("%d/%m/%Y"), name, yob, "", f"'{phone}", pos, "Mới nhận", note, source, link
                    ])
                    st.success("Đã lưu!"); time.sleep(1); st.rerun()

def list_page():
    if st.button("⬅️ Quay về"): st.session_state.current_page = "Home"; st.rerun()
    st.header("📋 Danh Sách Hồ Sơ")
    
    df = pd.DataFrame(sheet_ungvien.get_all_records())
    if not df.empty:
        search = st.text_input("🔍 Tìm kiếm tên hoặc SĐT...")
        if search:
            df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
        for i, row in df.iterrows():
            with st.expander(f"{row['HoTen']} - {row['ViTri']}"):
                c1, c2 = st.columns([1,3])
                c1.image(row['LinkAnh'] if row.get('LinkAnh') else "https://via.placeholder.com/150", width=100)
                c2.write(f"📞 {row['SDT']} | 📅 {row.get('NgayNhap','')}")
                c2.info(f"Note: {row.get('GhiChu','')}")

def admin_page():
    if st.button("⬅️ Quay về"): st.session_state.current_page = "Home"; st.rerun()
    st.header("⚙️ Quản Trị Hệ Thống")
    
    # Chỉ Admin mới được vào sâu
    if st.session_state.user_role != "admin":
        st.warning("Bạn là Manager, chỉ được xem báo cáo, không được chỉnh sửa User.")
        return

    st.subheader("1. Danh sách nhân viên")
    users = sheet_users.get_all_records()
    df_users = pd.DataFrame(users)
    st.dataframe(df_users)

    st.markdown("---")
    st.subheader("2. Phân Quyền (Set Role)")
    st.info("Chọn tên đăng nhập của nhân viên và cấp quyền mới cho họ.")
    
    with st.form("update_role_form"):
        # Lấy danh sách username
        user_list = [u['Username'] for u in users]
        selected_user = st.selectbox("Chọn nhân viên cần sửa:", user_list)
        new_role = st.selectbox("Chọn quyền mới:", ["staff", "manager", "admin"])
        
        if st.form_submit_button("Cập nhật quyền"):
            try:
                # Tìm dòng chứa username đó để sửa
                cell = sheet_users.find(selected_user)
                # Cột Role là cột thứ 3 (C)
                sheet_users.update_cell(cell.row, 3, new_role)
                st.success(f"Đã thăng chức cho {selected_user} thành {new_role}!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")

# --- ĐIỀU HƯỚNG ---
if not st.session_state.logged_in:
    login_screen()
else:
    if st.session_state.current_page == "Home": home_screen()
    elif st.session_state.current_page == "Input": input_page()
    elif st.session_state.current_page == "List": list_page()
    elif st.session_state.current_page == "Admin": admin_page()
    elif st.session_state.current_page == "Report": 
        st.title("📊 Báo Cáo"); st.button("⬅️ Quay về", on_click=lambda: st.session_state.update(current_page="Home"))
