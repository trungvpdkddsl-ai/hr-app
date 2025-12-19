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
st.set_page_config(page_title="HR Admin Pro", layout="wide", page_icon="🎯")

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
    
    /* SUCCESS TAG */
    .status-tag {
        padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;
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
    df = pd.DataFrame(sheet_ungvien.get_all_records())

    # --- SIDEBAR MENU ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"Vai trò: {st.session_state.user_role.upper()}")
        st.markdown("---")
        
        if st.button("🏠 TỔNG QUAN SYSTEM"): set_page("dashboard")
        if st.button("📝 NHẬP HỒ SƠ MỚI"): set_page("input")
        if st.button("🔍 LỌC & DANH SÁCH"): set_page("list")
        if st.button("🖩 TÍNH LƯƠNG"): set_page("salary")
        
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
                st.subheader("🏆 Top Nhân Viên Tuyển Dụng")
                if 'NguoiTuyen' in df.columns:
                    st.bar_chart(df['NguoiTuyen'].value_counts())
            with c2:
                st.subheader("🎯 Nguồn Ứng Viên")
                st.dataframe(df['Nguồn'].value_counts(), use_container_width=True)

    # --- PAGE 2: NHẬP LIỆU (ĐÃ SỬA: NGÀY SINH, TIKTOK, VỊ TRÍ KHÁC) ---
    elif st.session_state.current_page == "input":
        st.header("📝 Nhập Hồ Sơ Ứng Viên Mới")
        
        with st.container(border=True):
            with st.form("input_form"):
                # Hàng 1: Ảnh & Info cơ bản
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
                # Hàng 2: Chi tiết (Đã sửa Năm sinh thành Ngày sinh)
                r1, r2, r3 = st.columns(3)
                # SỬA 1: Ngày sinh chi tiết
                dob = r1.date_input("Ngày tháng năm sinh", value=date(2000, 1, 1), min_value=date(1960, 1, 1))
                hometown = r2.text_input("Quê quán")
                # SỬA 2: Thêm "Khác" vào vị trí
                pos = r3.selectbox("Vị trí ứng tuyển", ["Công nhân may", "Lắp ráp điện tử", "Kỹ thuật", "Kho", "Bảo vệ", "Tạp vụ", "Khác"])
                
                # Hàng 3: Nguồn & Social (Đã thêm lại TikTok)
                r4, r5, r6 = st.columns(3)
                source = r4.selectbox("Nguồn", ["Facebook", "Zalo", "TikTok", "Trực tiếp", "Giới thiệu"])
                fb = r5.text_input("Link Facebook")
                # SỬA 3: Thêm lại TikTok
                tt = r6.text_input("Link TikTok") 

                # Hàng 4: Hậu cần
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
                                 # Format lại ngày sinh thành chuỗi ngày/tháng/năm
                                 dob_str = dob.strftime("%d/%m/%Y")
                                 
                                 row = [
                                     datetime.now().strftime("%d/%m/%Y"), # 1.NgayNhap
                                     name.upper(),                        # 2.HoTen
                                     dob_str,                             # 3.NamSinh (Giờ là NgàySinh)
                                     hometown, f"'{phone}", f"'{cccd}",   # 4,5,6
                                     pos, "Mới nhận", "", source,         # 7,8,9,10
                                     link, bus, ktx,                      # 11,12,13
                                     st.session_state.user_name,          # 14.User
                                     fb, tt, doc                          # 15.FB, 16.TikTok, 17.GiayTo
                                 ]
                                 sheet_ungvien.append_row(row)
                                 st.success("✅ Đã lưu thành công!")
                                 time.sleep(1); st.rerun()
                    else: st.error("Vui lòng điền đủ Tên, SĐT và CCCD!")

    # --- PAGE 3: DANH SÁCH & LỌC NÂNG CAO (TÍNH NĂNG MỚI) ---
    elif st.session_state.current_page == "list":
        st.header("🔍 Tra Cứu & Lọc Hồ Sơ")
        
        if not df.empty:
            # --- BỘ LỌC NÂNG CAO ---
            with st.expander("🔻 BỘ LỌC TÙY CHỌN (Bấm để mở rộng)", expanded=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                
                # Lọc Trạng Thái
                status_options = ["Tất cả"] + list(df['TrangThai'].unique())
                filter_status = col_f1.multiselect("Lọc theo Trạng thái:", df['TrangThai'].unique(), default=[])
                
                # Lọc Vị Trí
                filter_pos = col_f2.multiselect("Lọc theo Vị trí:", df['ViTri'].unique())
                
                # Lọc Nguồn
                filter_source = col_f3.multiselect("Lọc theo Nguồn:", df['Nguồn'].unique())
                
                # Ô tìm kiếm từ khóa
                search_query = st.text_input("🔎 Tìm chi tiết (Tên, SĐT, CCCD):")

            # --- XỬ LÝ LOGIC LỌC ---
            df_filtered = df.copy()
            
            if filter_status:
                df_filtered = df_filtered[df_filtered['TrangThai'].isin(filter_status)]
            if filter_pos:
                df_filtered = df_filtered[df_filtered['ViTri'].isin(filter_pos)]
            if filter_source:
                df_filtered = df_filtered[df_filtered['Nguồn'].isin(filter_source)]
            if search_query:
                df_filtered = df_filtered[df_filtered.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

            # --- HIỂN THỊ KẾT QUẢ ---
            st.markdown(f"**👉 Tìm thấy: {len(df_filtered)} hồ sơ phù hợp**")
            
            # Nút tải file Excel cho danh sách đã lọc
            csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Tải danh sách này về Excel", csv, "ds_loc.csv", "text/csv")

            # Hiển thị dạng bảng (Table)
            st.dataframe(
                df_filtered[['HoTen', 'NamSinh', 'SDT', 'ViTri', 'TrangThai', 'Nguồn']], 
                use_container_width=True, 
                hide_index=True
            )
            
            # Hiển thị chi tiết dạng Thẻ (Card)
            st.markdown("---")
            for i, row in df_filtered.iterrows():
                with st.expander(f"👤 {row['HoTen']} - {row['TrangThai']}"):
                    ec1, ec2, ec3 = st.columns([1, 2, 1])
                    with ec1:
                        if row.get('LinkAnh'): st.image(row['LinkAnh'], width=100)
                        st.image(generate_qr(f"{row['HoTen']}"), width=80, caption="QR Hồ sơ")
                    with ec2:
                        st.write(f"📅 **Ngày sinh:** {row['NamSinh']}")
                        st.write(f"📞 **SĐT:** {row['SDT']} | 🆔 **CCCD:** {row.get('CCCD')}")
                        st.write(f"🏠 **Quê:** {row['QueQuan']}")
                        st.info(f"Ghi chú: {row.get('GhiChu')}")
                    with ec3:
                         st.write("**Social Links:**")
                         if row.get('LinkTikTok'): st.markdown(f"🎵 [TikTok]({row['LinkTikTok']})")
                         if row.get('LinkFB'): st.markdown(f"🌐 [Facebook]({row['LinkFB']})")

    # --- PAGE 4: TÍNH LƯƠNG ---
    elif st.session_state.current_page == "salary":
        st.header("🖩 Tính Lương Nhanh")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            lcb = c1.number_input("Lương cơ bản", 4500000)
            pc = c1.number_input("Phụ cấp", 1000000)
            ot = c2.number_input("Giờ OT", 40)
            total = lcb + pc + ((lcb/26/8)*ot*1.5)
            st.metric("Tổng Thực Nhận", f"{int(total):,} VNĐ")

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
