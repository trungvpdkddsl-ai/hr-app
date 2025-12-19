import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import time
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="HR Pro Dashboard", layout="wide", page_icon="🏢")

# --- CẤU HÌNH ID DRIVE (GIỮ NGUYÊN CỦA BẠN) ---
FOLDER_ID_DRIVE = "1Sw91t5o-m8fwZsbGpJw8Yex_WzV8etCx"

# --- CSS LÀM ĐẸP GIAO DIỆN ---
st.markdown("""
    <style>
    /* Chỉnh sửa Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f0f2f6;
        border-right: 1px solid #dcdcdc;
    }
    .user-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        text-align: center;
    }
    .user-role {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    .admin-role {
        background-color: #ffebee;
        color: #c62828;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
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
    except Exception:
        return None, None

client, drive_service = get_gcp_service()

if not client:
    st.error("⚠️ Lỗi kết nối! Kiểm tra lại Secrets.")
    st.stop()

try:
    sheet_ungvien = client.open("TuyenDungKCN_Data").worksheet("UngVien")
    sheet_users = client.open("TuyenDungKCN_Data").worksheet("Users")
except:
    st.error("⚠️ Không tìm thấy Sheet 'UngVien' hoặc 'Users'.")
    st.stop()

# --- HÀM UPLOAD ẢNH ---
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

# ==========================================
# 1. MÀN HÌNH ĐĂNG NHẬP (GIỮ NGUYÊN)
# ==========================================
def login_screen():
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<h2 style='text-align: center;'>🔐 HR SYSTEM</h2>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Đăng Nhập", "Đăng Ký"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Đăng Nhập", use_container_width=True):
                    users = sheet_users.get_all_records()
                    found = False
                    for user in users:
                        if str(user['Username']) == username and str(user['Password']) == password:
                            st.session_state.logged_in = True
                            st.session_state.user_role = user['Role']
                            st.session_state.user_name = user['HoTen']
                            found = True
                            st.rerun()
                    if not found:
                        st.error("Sai thông tin!")

        with tab2:
            with st.form("reg_form"):
                new_u = st.text_input("Tên đăng nhập mới")
                new_p = st.text_input("Mật khẩu mới", type="password")
                new_n = st.text_input("Họ tên nhân viên")
                if st.form_submit_button("Đăng Ký", use_container_width=True):
                    users = sheet_users.col_values(1)
                    if new_u in users:
                        st.warning("Tên này đã có người dùng.")
                    else:
                        sheet_users.append_row([new_u, new_p, "staff", new_n])
                        st.success("Tạo tài khoản thành công! Hãy đăng nhập.")

# ==========================================
# 2. GIAO DIỆN CHÍNH (SIDEBAR NAV)
# ==========================================
def main_app():
    # --- SIDEBAR TRÁI ---
    with st.sidebar:
        # Thẻ thông tin User
        role_class = "admin-role" if st.session_state.user_role == "admin" else "user-role"
        st.markdown(f"""
        <div class="user-card">
            <h3>👤 {st.session_state.user_name}</h3>
            <span class="{role_class}">{st.session_state.user_role.upper()}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Menu điều hướng
        st.caption("MENU CHÍNH")
        
        menu_options = ["🏠 Trang Chủ", "📝 Nhập Hồ Sơ", "📋 Danh Sách", "📊 Báo Cáo"]
        if st.session_state.user_role == "admin":
            menu_options.append("⚙️ Quản Trị Hệ Thống")
            
        selected_page = st.radio("", menu_options, label_visibility="collapsed")
        
        st.markdown("---")
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # --- NỘI DUNG CHÍNH (BÊN PHẢI) ---
    
    # 1. TRANG CHỦ
    if "Trang Chủ" in selected_page:
        st.title("👋 Bảng Tin Tuyển Dụng")
        st.info("Chào mừng bạn quay trở lại làm việc. Hãy chọn chức năng ở menu bên trái.")
        
        # Thống kê nhanh
        df = pd.DataFrame(sheet_ungvien.get_all_records())
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng hồ sơ", len(df))
            c2.metric("Mới nhận hôm nay", len(df[df['NgayNhap'].astype(str).str.contains(datetime.now().strftime("%d/%m/%Y"))]))
            c3.metric("Chờ phỏng vấn", len(df[df['TrangThai'] == 'Mới nhận']))

    # 2. NHẬP HỒ SƠ
    elif "Nhập Hồ Sơ" in selected_page:
        st.header("📝 Tiếp Nhận Ứng Viên")
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                uploaded_file = st.file_uploader("Ảnh chân dung", type=['jpg', 'png'])
                if uploaded_file: st.image(uploaded_file, width=150)
            with c2:
                name = st.text_input("Họ tên (*)")
                phone = st.text_input("SĐT (*)")
                yob = st.number_input("Năm sinh", 1970, 2010, 2000)
            
            c3, c4 = st.columns(2)
            pos = c3.selectbox("Vị trí", ["Công nhân may", "Lắp ráp điện tử", "Kỹ thuật", "Bảo vệ", "Tạp vụ"])
            source = c4.selectbox("Nguồn", ["Facebook", "Zalo", "Giới thiệu", "Trực tiếp"])
            note = st.text_area("Ghi chú phỏng vấn")
            
            if st.button("Lưu Hồ Sơ", type="primary"):
                if name and phone:
                    with st.spinner("Đang lưu..."):
                        link = ""
                        if uploaded_file:
                            link = upload_to_drive(uploaded_file, f"{name}_{phone}.jpg")
                        
                        sheet_ungvien.append_row([
                            datetime.now().strftime("%d/%m/%Y"), name, yob, "", f"'{phone}", pos, "Mới nhận", note, source, link
                        ])
                        st.success("Đã thêm mới thành công!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Thiếu Tên hoặc SĐT!")

    # 3. DANH SÁCH
    elif "Danh Sách" in selected_page:
        st.header("📋 Cơ Sở Dữ Liệu")
        df = pd.DataFrame(sheet_ungvien.get_all_records())
        
        if not df.empty:
            col_search, col_filter = st.columns([3, 1])
            search = col_search.text_input("🔍 Tìm kiếm tên hoặc số điện thoại", placeholder="Nhập từ khóa...")
            filter_stt = col_filter.selectbox("Lọc trạng thái", ["Tất cả"] + list(df['TrangThai'].unique()))
            
            # Xử lý lọc
            if search:
                df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            if filter_stt != "Tất cả":
                df = df[df['TrangThai'] == filter_stt]
            
            # Hiển thị bảng
            st.dataframe(
                df[['NgayNhap', 'HoTen', 'NamSinh', 'SDT', 'ViTri', 'TrangThai', 'Nguồn']], 
                use_container_width=True,
                hide_index=True
            )
            
            # Hiển thị chi tiết (Có ảnh)
            st.markdown("---")
            st.subheader("Chi tiết hồ sơ (kèm ảnh)")
            for i, row in df.iterrows():
                with st.expander(f"👤 {row['HoTen']} - {row['ViTri']}"):
                    kc1, kc2 = st.columns([1, 4])
                    with kc1:
                        if row.get('LinkAnh'):
                            st.image(row['LinkAnh'], width=120)
                        else:
                            st.write("🚫 Không ảnh")
                    with kc2:
                        st.write(f"**SĐT:** {row['SDT']}")
                        st.write(f"**Ghi chú:** {row.get('GhiChu', '')}")
                        # Có thể thêm nút cập nhật trạng thái ở đây sau này

    # 4. BÁO CÁO
    elif "Báo Cáo" in selected_page:
        st.header("📊 Báo Cáo Hiệu Quả")
        df = pd.DataFrame(sheet_ungvien.get_all_records())
        if not df.empty:
            tab_a, tab_b = st.tabs(["Theo Vị Trí", "Theo Nguồn"])
            with tab_a:
                st.bar_chart(df['ViTri'].value_counts())
            with tab_b:
                st.bar_chart(df['Nguồn'].value_counts())
        else:
            st.info("Chưa có dữ liệu.")

    # 5. QUẢN TRỊ (CHỈ ADMIN)
    elif "Quản Trị" in selected_page:
        st.header("⚙️ Phân Quyền Nhân Viên")
        
        users = sheet_users.get_all_records()
        df_users = pd.DataFrame(users)
        st.dataframe(df_users, use_container_width=True)
        
        st.markdown("### Cập nhật quyền hạn")
        with st.form("admin_tool"):
            c1, c2 = st.columns(2)
            u_select = c1.selectbox("Chọn nhân viên", [u['Username'] for u in users])
            r_select = c2.selectbox("Chọn quyền mới", ["staff", "admin"])
            
            if st.form_submit_button("Cập nhật ngay"):
                cell = sheet_users.find(u_select)
                sheet_users.update_cell(cell.row, 3, r_select) # Cột 3 là Role
                st.success(f"Đã set quyền {r_select} cho {u_select}")
                time.sleep(1)
                st.rerun()

# --- CHẠY APP ---
if st.session_state.logged_in:
    main_app()
else:
    login_screen()
