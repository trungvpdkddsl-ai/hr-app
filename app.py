import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import time
from datetime import datetime, date
import qrcode
from io import BytesIO

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="HR Admin Pro", layout="wide", page_icon="🗂️")

# --- CẤU HÌNH ID DRIVE ---
FOLDER_ID_DRIVE = "1Sw91t5o-m8fwZsbGpJw8Yex_WzV8etCx"

# --- CSS GIAO DIỆN ---
st.markdown("""
    <style>
    /* SIDEBAR STYLE */
    [data-testid="stSidebar"] {background-color: #f8f9fa; border-right: 1px solid #dee2e6;}
    [data-testid="stSidebar"] .stButton > button {
        width: 100%; height: 60px; border: none; border-radius: 10px;
        background-color: white; color: #495057; font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: left; padding-left: 20px;
        transition: all 0.3s; margin-bottom: 10px;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #e3f2fd; color: #0d47a1; transform: translateX(5px);
    }
    [data-testid="stSidebar"] .stButton > button:focus {
        border-left: 5px solid #0d47a1; background-color: #e3f2fd;
    }

    /* CARD REPORT STYLE */
    .metric-container {display: flex; gap: 10px; margin-bottom: 20px;}
    .metric-card {
        background: white; padding: 15px; border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); flex: 1; text-align: center; border-top: 4px solid #2196F3;
    }
    .metric-val { font-size: 28px; font-weight: bold; color: #333; }
    .metric-lbl { font-size: 14px; color: #666; text-transform: uppercase; }

    /* SOCIAL BUTTONS */
    .social-btn {
        display: inline-block; padding: 3px 8px; border-radius: 4px; color: white !important;
        text-decoration: none; font-size: 11px; margin-right: 4px; font-weight: bold;
    }
    .zalo {background-color: #0068FF;} .fb {background-color: #1877F2;} .tiktok {background-color: #000000;}
    
    /* GALLERY STYLE */
    .gallery-card {
        background: white; padding: 10px; border-radius: 8px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px;
    }
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

# KẾT NỐI CÁC SHEET
try:
    sheet_ungvien = client.open("TuyenDungKCN_Data").worksheet("UngVien")
    sheet_users = client.open("TuyenDungKCN_Data").worksheet("Users")
    # Kết nối thêm sheet Kho Ảnh mới
    sheet_storage = client.open("TuyenDungKCN_Data").worksheet("KhoAnh")
except: 
    st.error("⚠️ Lỗi: Không tìm thấy Sheet! Hãy chắc chắn bạn đã tạo Tab tên là 'KhoAnh'.")
    st.stop()

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
    st.markdown("<br><h1 style='text-align: center; color:#0d47a1'>🔐 HR ADMIN PRO</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        with st.form("login"):
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

# --- MAIN APP ---
def main_app():
    # Load data Ung Vien
    df = pd.DataFrame(sheet_ungvien.get_all_records())

    # --- SIDEBAR MENU ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"Vai trò: {st.session_state.user_role.upper()}")
        st.markdown("---")
        
        if st.button("🏠 TỔNG QUAN SYSTEM"): set_page("dashboard")
        if st.button("📝 NHẬP HỒ SƠ MỚI"): set_page("input")
        if st.button("🔍 LỌC & DANH SÁCH"): set_page("list")
        
        # Nút mới: KHO ẢNH
        if st.button("📂 KHO ẢNH MEDIA"): set_page("storage")
        
        if st.session_state.user_role == "admin":
            st.markdown("---")
            if st.button("⚙️ QUẢN TRỊ USER"): set_page("admin")
            
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất"): st.session_state.logged_in = False; st.rerun()

    # --- PAGE 1: DASHBOARD ---
    if st.session_state.current_page == "dashboard":
        st.title("📊 Bảng Điều Khiển Trung Tâm")
        st.markdown(f"Dữ liệu cập nhật: {datetime.now().strftime('%d/%m/%Y')}")
        
        if not df.empty:
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
            </div>
            """.format(len(df), len(df[df['TrangThai']=='Đã đi làm']), len(df[df['TrangThai']=='Mới nhận'])), unsafe_allow_html=True)
            
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("🏆 Top Nhân Viên")
                if 'NguoiTuyen' in df.columns: st.bar_chart(df['NguoiTuyen'].value_counts())
            with c2:
                st.subheader("🎯 Nguồn Ứng Viên")
                st.dataframe(df['Nguồn'].value_counts(), use_container_width=True)

    # --- PAGE 2: NHẬP LIỆU ---
    elif st.session_state.current_page == "input":
        st.header("📝 Nhập Hồ Sơ Ứng Viên Mới")
        with st.container(border=True):
            with st.form("input_form"):
                c_img, c_info = st.columns([1, 3])
                with c_img:
                    uploaded_file = st.file_uploader("Ảnh chân dung", type=['jpg','png'])
                    if uploaded_file: st.image(uploaded_file, width=150)
                with c_info:
                    c1, c2 = st.columns(2)
                    name = c1.text_input("Họ tên (*)")
                    phone = c2.text_input("SĐT (*)")
                    cccd = st.text_input("Số CCCD/CMND (*)")

                st.markdown("---")
                r1, r2, r3 = st.columns(3)
                dob = r1.date_input("Ngày sinh", value=date(2000, 1, 1), min_value=date(1960, 1, 1))
                hometown = r2.text_input("Quê quán")
                pos = r3.selectbox("Vị trí", ["Công nhân may", "Lắp ráp điện tử", "Kỹ thuật", "Kho", "Bảo vệ", "Tạp vụ", "Khác"])
                
                r4, r5, r6 = st.columns(3)
                source = r4.selectbox("Nguồn", ["Facebook", "Zalo", "TikTok", "Trực tiếp", "Giới thiệu"])
                fb = r5.text_input("Link Facebook")
                tt = r6.text_input("Link TikTok") 

                r7, r8, r9 = st.columns(3)
                bus = r7.selectbox("Xe tuyến", ["Tự túc", "Tuyến A", "Tuyến B"])
                doc = r8.selectbox("Giấy tờ", ["Chưa có", "Đủ giấy tờ", "Thiếu khám SK"])
                ktx = r9.selectbox("Ở Ký túc xá?", ["Không", "Có đăng ký"])

                if st.form_submit_button("LƯU HỒ SƠ NGAY", type="primary"):
                    if name and phone and cccd:
                         if not df.empty and str(cccd) in df['CCCD'].astype(str).values:
                             st.warning("⚠️ Trùng CCCD! Người này đã có trong hệ thống.")
                         else:
                             with st.spinner("Đang lưu..."):
                                 link = upload_to_drive(uploaded_file, f"{name}.jpg") if uploaded_file else ""
                                 dob_str = dob.strftime("%d/%m/%Y")
                                 row = [
                                     datetime.now().strftime("%d/%m/%Y"), name.upper(), dob_str,
                                     hometown, f"'{phone}", f"'{cccd}", pos, "Mới nhận", "", source,
                                     link, bus, ktx, st.session_state.user_name, fb, tt, doc
                                 ]
                                 sheet_ungvien.append_row(row)
                                 st.success("✅ Đã lưu thành công!"); time.sleep(1); st.rerun()
                    else: st.error("Vui lòng điền đủ Tên, SĐT và CCCD!")

    # --- PAGE 3: DANH SÁCH ---
    elif st.session_state.current_page == "list":
        st.header("🔍 Tra Cứu & Lọc Hồ Sơ")
        if not df.empty:
            with st.expander("🔻 BỘ LỌC TÙY CHỌN", expanded=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                filter_status = col_f1.multiselect("Trạng thái:", df['TrangThai'].unique())
                filter_pos = col_f2.multiselect("Vị trí:", df['ViTri'].unique())
                search_query = st.text_input("🔎 Tìm chi tiết (Tên, SĐT, CCCD):")

            df_filtered = df.copy()
            if filter_status: df_filtered = df_filtered[df_filtered['TrangThai'].isin(filter_status)]
            if filter_pos: df_filtered = df_filtered[df_filtered['ViTri'].isin(filter_pos)]
            if search_query: df_filtered = df_filtered[df_filtered.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

            st.markdown(f"**👉 Tìm thấy: {len(df_filtered)} hồ sơ**")
            st.dataframe(df_filtered[['HoTen', 'NamSinh', 'SDT', 'ViTri', 'TrangThai']], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            for i, row in df_filtered.iterrows():
                with st.expander(f"👤 {row['HoTen']} - {row['TrangThai']}"):
                    ec1, ec2, ec3 = st.columns([1, 2, 1])
                    with ec1:
                        if row.get('LinkAnh'): st.image(row['LinkAnh'], width=100)
                        st.image(generate_qr(f"{row['HoTen']}"), width=80)
                    with ec2:
                        st.write(f"📅 {row['NamSinh']} | 📞 {row['SDT']} | 🆔 {row.get('CCCD')}")
                        st.write(f"🏠 {row['QueQuan']}")
                        if row.get('LinkFB'): st.markdown(f"🌐 [Facebook]({row['LinkFB']})")
                    with ec3:
                         st.info(f"Nguồn: {row['Nguồn']}")

    # --- PAGE 4: KHO ẢNH (TÍNH NĂNG MỚI) ---
    elif st.session_state.current_page == "storage":
        st.header("📂 Kho Ảnh Marketing (Facebook/Zalo)")
        st.caption("Nơi lưu trữ banner, hình ảnh hoạt động công ty để đăng bài tuyển dụng.")
        
        # 1. Upload ảnh mới
        with st.expander("⬆️ Tải ảnh mới lên Kho", expanded=False):
            with st.form("upload_storage"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    img_file = st.file_uploader("Chọn ảnh", type=['jpg', 'png', 'jpeg'])
                with c2:
                    img_name = st.text_input("Tên gợi nhớ (VD: Banner T8, Anh du lich he...)")
                    img_note = st.text_area("Ghi chú (Nội dung đăng bài...)")
                
                if st.form_submit_button("Lưu vào Kho"):
                    if img_file and img_name:
                        with st.spinner("Đang tải lên..."):
                            # Thêm tiền tố MKT_ để phân biệt trên Drive
                            file_path = f"MKT_{img_name}_{datetime.now().strftime('%Y%m%d')}.jpg"
                            link = upload_to_drive(img_file, file_path)
                            
                            if link:
                                # Lưu vào sheet KhoAnh
                                sheet_storage.append_row([
                                    datetime.now().strftime("%d/%m/%Y"),
                                    img_name,
                                    link,
                                    img_note
                                ])
                                st.success("✅ Đã lưu ảnh thành công!")
                                time.sleep(1); st.rerun()
                            else:
                                st.error("Lỗi upload Drive!")
                    else:
                        st.warning("Vui lòng chọn ảnh và đặt tên!")

        # 2. Hiển thị Gallery
        st.markdown("---")
        try:
            storage_data = sheet_storage.get_all_records()
            df_store = pd.DataFrame(storage_data)
            
            if not df_store.empty:
                # Hiển thị dạng lưới 3 cột
                cols = st.columns(3)
                for idx, row in df_store.iterrows():
                    with cols[idx % 3]: # Chia đều vào 3 cột
                        with st.container(border=True):
                            if row.get('LinkAnh'):
                                st.image(row['LinkAnh'], use_container_width=True)
                            st.markdown(f"**{row['TenAnh']}**")
                            st.caption(f"📅 {row['NgayUp']}")
                            with st.expander("Xem nội dung"):
                                st.write(row['GhiChu'])
                                st.code(row['LinkAnh'], language="text") # Để copy link nhanh
            else:
                st.info("Kho ảnh đang trống. Hãy tải ảnh đầu tiên lên!")
        except Exception as e:
            st.error("Chưa có dữ liệu hoặc lỗi đọc Sheet 'KhoAnh'.")

    # --- PAGE 5: ADMIN ---
    elif st.session_state.current_page == "admin":
        st.header("⚙️ Quản Trị Hệ Thống")
        users = sheet_users.get_all_records()
        st.dataframe(users, use_container_width=True)
        with st.form("edit_role"):
            u = st.selectbox("Username", [x['Username'] for x in users])
            r = st.selectbox("Quyền mới", ["staff", "admin"])
            if st.form_submit_button("Cập nhật"):
                cell = sheet_users.find(u); sheet_users.update_cell(cell.row, 3, r)
                st.success("Xong!"); time.sleep(1); st.rerun()

# --- RUN ---
if st.session_state.logged_in: main_app()
else: login_screen()
