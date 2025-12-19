import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import time
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="HR KCN Ultimate", layout="wide", page_icon="🏭")

# --- CẤU HÌNH ID DRIVE (GIỮ NGUYÊN) ---
FOLDER_ID_DRIVE = "1Sw91t5o-m8fwZsbGpJw8Yex_WzV8etCx"

# --- CSS TÙY CHỈNH CAO CẤP ---
st.markdown("""
    <style>
    /* Nút Zalo màu xanh đặc trưng */
    .zalo-btn {
        display: inline-block;
        background-color: #0068FF;
        color: white;
        padding: 5px 15px;
        text-decoration: none;
        border-radius: 20px;
        font-weight: bold;
        margin-top: 5px;
    }
    .zalo-btn:hover {background-color: #0054d1; color: white;}
    
    /* Thẻ thông tin KPI */
    .kpi-card {
        background-color: #fff3e0;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff9800;
        margin-bottom: 10px;
    }
    
    /* Sidebar user profile */
    .user-profile {
        background: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
    st.error("⚠️ Không tìm thấy Sheet! Hãy chắc chắn bạn đã tạo file và đổi tên tab đúng.")
    st.stop()

# --- CÁC HÀM HỖ TRỢ ---
def upload_to_drive(file_obj, file_name):
    try:
        metadata = {'name': file_name, 'parents': [FOLDER_ID_DRIVE]}
        media = MediaIoBaseUpload(file_obj, mimetype=file_obj.type)
        file = drive_service.files().create(body=metadata, media_body=media, fields='webContentLink').execute()
        return file.get('webContentLink')
    except:
        return None

def format_zalo_link(phone):
    """Chuyển đổi SĐT 09xx -> link Zalo 849xx"""
    p = str(phone).replace("'", "").strip()
    if p.startswith("0"):
        p = "84" + p[1:]
    return f"https://zalo.me/{p}"

def check_blacklist(cccd, df):
    """Kiểm tra xem CCCD có nằm trong danh sách đen không"""
    # Ở đây ta giả lập logic: Nếu Status cũ là "Vĩnh viễn không tuyển" thì báo động
    if df.empty: return False
    blacklist_users = df[df['TrangThai'] == "Vĩnh viễn không tuyển"]
    if str(cccd) in blacklist_users['CCCD'].astype(str).values:
        return True
    return False

# --- QUẢN LÝ SESSION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = None

# ==========================================
# 1. LOGIN SCREEN
# ==========================================
def login_screen():
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("<h2 style='text-align: center;'>🏭 HR KCN PRO</h2>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Đăng Nhập", "Đăng Ký"])
        
        with tab1:
            with st.form("login"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Đăng nhập", use_container_width=True):
                    users = sheet_users.get_all_records()
                    for user in users:
                        if str(user['Username']) == u and str(user['Password']) == p:
                            st.session_state.logged_in = True
                            st.session_state.user_role = user['Role']
                            st.session_state.user_name = user['HoTen']
                            st.rerun()
                    st.error("Sai thông tin!")
        with tab2:
            with st.form("reg"):
                nu = st.text_input("User mới")
                np = st.text_input("Pass mới", type="password")
                nn = st.text_input("Họ tên")
                if st.form_submit_button("Đăng ký"):
                    sheet_users.append_row([nu, np, "staff", nn])
                    st.success("Tạo xong! Mời đăng nhập.")

# ==========================================
# 2. MAIN APP
# ==========================================
def main_app():
    # --- SIDEBAR ---
    with st.sidebar:
        # Profile Card
        role_label = "QUẢN TRỊ VIÊN 🔴" if st.session_state.user_role == "admin" else "NHÂN VIÊN 🔵"
        st.markdown(f"""
            <div class="user-profile">
                <h3>{st.session_state.user_name}</h3>
                <div style='font-weight:bold;'>{role_label}</div>
            </div>
        """, unsafe_allow_html=True)
        
        menu = st.radio("MENU", ["🏠 Trang Chủ", "📝 Nhập Hồ Sơ", "📋 Danh Sách & Zalo", "📊 Báo Cáo & KPI", "⚙️ Quản Trị"])
        
        st.markdown("---")
        if st.button("Đăng xuất"):
            st.session_state.logged_in = False
            st.rerun()

    # --- TẢI DỮ LIỆU CHUNG ---
    df = pd.DataFrame(sheet_ungvien.get_all_records())
    
    # 1. TRANG CHỦ (DASHBOARD)
    if "Trang Chủ" in menu:
        st.title("🚀 Bảng Điều Khiển")
        
        # KPI Tracker
        target = 100 # Mục tiêu ví dụ
        current = len(df) if not df.empty else 0
        progress = min(current / target, 1.0)
        
        st.markdown(f"**🔥 Tiến độ tuyển dụng tháng này: {current}/{target} nhân sự**")
        st.progress(progress)
        
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng hồ sơ", current)
            c2.metric("Chờ phỏng vấn", len(df[df['TrangThai'] == 'Mới nhận']))
            c3.metric("Đã đi làm", len(df[df['TrangThai'] == 'Đã đi làm']))

    # 2. NHẬP HỒ SƠ (NÂNG CẤP)
    elif "Nhập Hồ Sơ" in menu:
        st.header("📝 Tiếp Nhận Ứng Viên (Đầy đủ)")
        
        with st.form("input_full"):
            # Hàng 1: Ảnh và Thông tin cơ bản
            c1, c2 = st.columns([1, 2])
            with c1:
                uploaded_file = st.file_uploader("Ảnh chân dung", type=['jpg','png'])
                if uploaded_file: st.image(uploaded_file, width=130)
            with c2:
                name = st.text_input("Họ tên (*)")
                phone = st.text_input("Số điện thoại (*)")
                cccd = st.text_input("Số CCCD/CMND (*)", help="Dùng để check trùng và danh sách đen")
            
            # Hàng 2: Chi tiết
            c3, c4, c5 = st.columns(3)
            yob = c3.number_input("Năm sinh", 1970, 2010, 2000)
            hometown = c4.text_input("Quê quán (Tỉnh/Huyện)")
            pos = c5.selectbox("Vị trí", ["Công nhân may", "Điện tử", "Kho", "Bảo vệ", "Tạp vụ"])
            
            # Hàng 3: Hậu cần (MỚI)
            c6, c7, c8 = st.columns(3)
            bus = c6.selectbox("🚌 Xe tuyến", ["Tự túc", "Tuyến A (Ngã 4)", "Tuyến B (Cầu Giấy)", "Tuyến C (Bến xe)"])
            ktx = c7.selectbox("🏠 Ký túc xá", ["Không", "Có đăng ký"])
            source = c8.selectbox("Nguồn", ["Facebook", "Zalo", "Tờ rơi", "Giới thiệu", "Trực tiếp"])
            
            note = st.text_area("Ghi chú phỏng vấn")
            
            submitted = st.form_submit_button("LƯU HỒ SƠ", type="primary")
            
            if submitted:
                # 1. Check dữ liệu trống
                if not name or not phone or not cccd:
                    st.error("❌ Vui lòng điền Tên, SĐT và CCCD!")
                
                # 2. Check Trùng CCCD (Chống gian lận)
                elif not df.empty and str(cccd) in df['CCCD'].astype(str).values:
                    st.warning(f"⚠️ Cảnh báo: Số CCCD {cccd} đã tồn tại trong hệ thống!")
                
                # 3. Check Blacklist
                elif check_blacklist(cccd, df):
                    st.error(f"⛔ ỨNG VIÊN NẰM TRONG DANH SÁCH ĐEN! (CCCD: {cccd})")
                
                else:
                    with st.spinner("Đang lưu dữ liệu..."):
                        link = ""
                        if uploaded_file:
                            link = upload_to_drive(uploaded_file, f"{name}_{cccd}.jpg")
                        
                        # Lưu đủ 14 cột
                        row = [
                            datetime.now().strftime("%d/%m/%Y"), # 1. Ngay
                            name.upper(),                        # 2. Ten
                            yob,                                 # 3. NamSinh
                            hometown,                            # 4. QueQuan
                            f"'{phone}",                         # 5. SDT
                            f"'{cccd}",                          # 6. CCCD
                            pos,                                 # 7. ViTri
                            "Mới nhận",                          # 8. TrangThai
                            note,                                # 9. GhiChu
                            source,                              # 10. Nguồn
                            link,                                # 11. LinkAnh
                            bus,                                 # 12. XeTuyen
                            ktx,                                 # 13. KTX
                            st.session_state.user_name           # 14. NguoiTuyen (KPI)
                        ]
                        sheet_ungvien.append_row(row)
                        st.success("✅ Đã lưu hồ sơ mới thành công!")
                        time.sleep(1)
                        st.rerun()

    # 3. DANH SÁCH & ZALO
    elif "Danh Sách" in menu:
        st.header("📋 Quản Lý Hồ Sơ & Liên Hệ")
        
        # Công cụ lọc và xuất file
        col_tool1, col_tool2, col_tool3 = st.columns([2, 1, 1])
        search = col_tool1.text_input("🔍 Tìm tên, SĐT, CCCD...")
        
        # Nút xuất Excel (CSV)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        col_tool3.download_button(
            label="📥 Tải Excel báo cáo",
            data=csv,
            file_name='ds_tuyendung.csv',
            mime='text/csv',
        )
        
        # Xử lý tìm kiếm
        if not df.empty:
            if search:
                df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
            st.caption(f"Tìm thấy {len(df)} hồ sơ")
            
            # HIỂN THỊ DẠNG THẺ (CARD) ĐỂ TỐI ƯU TƯƠNG TÁC
            for i, row in df.iterrows():
                with st.expander(f"👤 {row['HoTen']} - {row['ViTri']} ({row['TrangThai']})"):
                    # Layout chi tiết
                    kc1, kc2, kc3 = st.columns([1, 2, 1])
                    with kc1:
                        if row.get('LinkAnh'): st.image(row['LinkAnh'], width=100)
                        else: st.write("🖼️ No Image")
                    
                    with kc2:
                        st.write(f"🆔 **CCCD:** {row.get('CCCD', '')}")
                        st.write(f"🏠 **Quê:** {row.get('QueQuan', '')} | **Năm sinh:** {row['NamSinh']}")
                        st.write(f"🚌 **Xe:** {row.get('XeTuyen', '')} | 🏠 **KTX:** {row.get('KTX', '')}")
                        st.info(f"📝 Note: {row.get('GhiChu', '')}")
                        
                    with kc3:
                        # Nút Zalo thần thánh
                        zalo_link = format_zalo_link(row['SDT'])
                        st.markdown(f'<a href="{zalo_link}" target="_blank" class="zalo-btn">💬 Chat Zalo</a>', unsafe_allow_html=True)
                        
                        # Kịch bản gọi điện
                        st.write("")
                        with st.popover("📞 Kịch bản gọi"):
                            st.markdown(f"""
                            **Kịch bản chào hỏi:**
                            *"Alo, chào em {row['HoTen']}. Chị gọi từ phòng nhân sự công ty...*
                            *Chị thấy em đăng ký vị trí {row['ViTri']}.*
                            *Em có thể đi phỏng vấn vào sáng mai lúc 8h không?"*
                            """)

    # 4. BÁO CÁO & KPI
    elif "Báo Cáo" in menu:
        st.header("📊 Báo Cáo Hiệu Quả & KPI Team")
        if not df.empty:
            tab1, tab2 = st.tabs(["🏆 Bảng Xếp Hạng", "📈 Biểu Đồ"])
            
            with tab1:
                st.subheader("Ai là người tuyển dụng giỏi nhất?")
                if 'NguoiTuyen' in df.columns:
                    kpi_counts = df['NguoiTuyen'].value_counts()
                    st.bar_chart(kpi_counts)
                else:
                    st.warning("Dữ liệu cũ chưa có cột 'Người tuyển'. Hãy nhập mới để thấy biểu đồ.")

            with tab2:
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Nguồn ứng viên hiệu quả**")
                    st.bar_chart(df['Nguồn'].value_counts())
                with c2:
                    st.write("**Trạng thái ứng viên**")
                    st.bar_chart(df['TrangThai'].value_counts())

    # 5. QUẢN TRỊ (ADMIN)
    elif "Quản Trị" in menu:
        if st.session_state.user_role != "admin":
            st.warning("⛔ Bạn không có quyền truy cập khu vực này!")
        else:
            st.header("⚙️ Phân Quyền Hệ Thống")
            users = sheet_users.get_all_records()
            st.dataframe(users)
            
            with st.form("set_role"):
                u = st.selectbox("Chọn nhân viên", [x['Username'] for x in users])
                r = st.selectbox("Cấp quyền", ["staff", "admin"])
                if st.form_submit_button("Cập nhật"):
                    cell = sheet_users.find(u)
                    sheet_users.update_cell(cell.row, 3, r)
                    st.success(f"Đã cập nhật cho {u}")
                    time.sleep(1)
                    st.rerun()

# --- RUN ---
if st.session_state.logged_in:
    main_app()
else:
    login_screen()
