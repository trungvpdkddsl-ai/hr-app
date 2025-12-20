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
st.set_page_config(page_title="HR Admin Pro", layout="wide", page_icon="🛡️")

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
    
    /* METRIC CARDS */
    .metric-container {display: flex; gap: 10px; margin-bottom: 20px;}
    .metric-card {
        background: white; padding: 15px; border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); flex: 1; text-align: center; border-top: 4px solid #2196F3;
    }
    .metric-val { font-size: 28px; font-weight: bold; color: #333; }
    .metric-lbl { font-size: 14px; color: #666; text-transform: uppercase; }
    
    /* COPY BOX */
    .copy-box { background-color: #e8f5e9; padding: 10px; border-radius: 5px; border: 1px dashed #4caf50; font-family: monospace; }
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
    except Exception as e: return None, None

client, drive_service = get_gcp_service()
if not client: st.error("⚠️ Lỗi kết nối API Google!"); st.stop()

# KẾT NỐI SHEETS
try:
    sheet_ungvien = client.open("TuyenDungKCN_Data").worksheet("UngVien")
    sheet_users = client.open("TuyenDungKCN_Data").worksheet("Users")
    # Kiểm tra xem các sheet phụ có tồn tại không, nếu không thì bỏ qua để tránh lỗi
    try: sheet_storage = client.open("TuyenDungKCN_Data").worksheet("KhoAnh")
    except: sheet_storage = None
    try: sheet_templates = client.open("TuyenDungKCN_Data").worksheet("MauBai")
    except: sheet_templates = None
except: 
    st.error("⚠️ Lỗi: Không tìm thấy file Excel 'TuyenDungKCN_Data'. Hãy kiểm tra lại tên file.")
    st.stop()

# --- HÀM HỖ TRỢ (ĐÃ SỬA LỖI UPLOAD) ---
def upload_to_drive(file_obj, file_name):
    # Hàm này được bọc kỹ để nếu lỗi thì chỉ báo warning chứ không làm sập app
    try:
        if not file_obj: return None
        metadata = {'name': file_name, 'parents': [FOLDER_ID_DRIVE]}
        media = MediaIoBaseUpload(file_obj, mimetype=file_obj.type)
        file = drive_service.files().create(body=metadata, media_body=media, fields='webContentLink').execute()
        return file.get('webContentLink')
    except Exception as e:
        # Nếu lỗi Quota (403), in ra console nhưng trả về None để chương trình chạy tiếp
        print(f"Lỗi upload: {e}") 
        return "ERROR_QUOTA" 

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
    st.markdown("<br><h1 style='text-align: center; color:#1565c0'>🔐 HỆ THỐNG TUYỂN DỤNG</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        tab1, tab2 = st.tabs(["ĐĂNG NHẬP", "ĐĂNG KÝ"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Tên đăng nhập")
                p = st.text_input("Mật khẩu", type="password")
                if st.form_submit_button("VÀO HỆ THỐNG", use_container_width=True):
                    users = sheet_users.get_all_records()
                    found = False
                    for user in users:
                        if str(user['Username']) == u and str(user['Password']) == p:
                            st.session_state.logged_in = True
                            st.session_state.user_role = user['Role']
                            st.session_state.user_name = user['HoTen']
                            found = True; st.rerun()
                    if not found: st.error("Sai thông tin đăng nhập!")
        with tab2:
            with st.form("reg"):
                nu = st.text_input("User mới"); np = st.text_input("Pass mới", type="password"); nn = st.text_input("Họ tên")
                if st.form_submit_button("TẠO TÀI KHOẢN", use_container_width=True):
                    existing = sheet_users.col_values(1)
                    if nu in existing: st.warning("Tên đăng nhập đã có người dùng!")
                    else:
                        sheet_users.append_row([nu, np, "staff", nn])
                        st.success("Đăng ký thành công! Hãy quay lại tab Đăng Nhập.")

# --- MAIN APP ---
def main_app():
    df = pd.DataFrame(sheet_ungvien.get_all_records())

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"Quyền hạn: {st.session_state.user_role.upper()}")
        st.markdown("---")
        
        if st.button("🏠 DASHBOARD TỔNG QUAN"): set_page("dashboard")
        if st.button("📝 NHẬP HỒ SƠ MỚI"): set_page("input")
        if st.button("🔍 DANH SÁCH & LỌC"): set_page("list")
        if st.button("📋 MẪU BÀI ĐĂNG"): set_page("templates")
        
        # Nút Kho Ảnh (Chỉ hiện nếu kết nối được sheet)
        if sheet_storage:
            if st.button("📂 KHO ẢNH MEDIA"): set_page("storage")
        
        if st.session_state.user_role == "admin":
            st.markdown("---")
            if st.button("⚙️ QUẢN TRỊ USER"): set_page("admin")
            
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất"): st.session_state.logged_in = False; st.rerun()

    # --- PAGE: DASHBOARD ---
    if st.session_state.current_page == "dashboard":
        st.title("📊 Tổng Quan Hệ Thống")
        if not df.empty:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-card" style="border-top-color: #2196F3;"><div class="metric-val">{len(df)}</div><div class="metric-lbl">Tổng Hồ Sơ</div></div>
                <div class="metric-card" style="border-top-color: #4CAF50;"><div class="metric-val">{len(df[df['TrangThai']=='Đã đi làm'])}</div><div class="metric-lbl">Đã Đi Làm</div></div>
                <div class="metric-card" style="border-top-color: #FF9800;"><div class="metric-val">{len(df[df['TrangThai']=='Mới nhận'])}</div><div class="metric-lbl">Mới Nhận</div></div>
            </div>""", unsafe_allow_html=True)
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("🏆 Top Tuyển Dụng")
                if 'NguoiTuyen' in df.columns: st.bar_chart(df['NguoiTuyen'].value_counts())
            with c2:
                st.subheader("🎯 Nguồn Ứng Viên")
                st.dataframe(df['Nguồn'].value_counts(), use_container_width=True)

    # --- PAGE: NHẬP LIỆU (ĐÃ FIX LỖI CRASH) ---
    elif st.session_state.current_page == "input":
        st.header("📝 Nhập Hồ Sơ Ứng Viên")
        with st.form("input_form"):
            col_img, col_info = st.columns([1, 3])
            with col_img:
                uploaded_file = st.file_uploader("Ảnh (Nếu lỗi thì bỏ qua)", type=['jpg','png'])
            with col_info:
                name = st.text_input("Họ tên (*)")
                phone = st.text_input("SĐT (*)")
                cccd = st.text_input("Số CCCD (*)")

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
            ktx = r9.selectbox("Ký túc xá", ["Không", "Có"])

            if st.form_submit_button("LƯU HỒ SƠ NGAY", type="primary"):
                if name and phone and cccd:
                    with st.spinner("Đang xử lý..."):
                        # Xử lý upload ảnh an toàn
                        link = ""
                        upload_status = "OK"
                        if uploaded_file:
                            result = upload_to_drive(uploaded_file, f"{name}.jpg")
                            if result == "ERROR_QUOTA":
                                upload_status = "FAIL"
                            elif result:
                                link = result
                        
                        # Lưu dữ liệu
                        dob_str = dob.strftime("%d/%m/%Y")
                        row = [datetime.now().strftime("%d/%m/%Y"), name.upper(), dob_str, hometown, 
                               f"'{phone}", f"'{cccd}", pos, "Mới nhận", "", source, link, bus, ktx, 
                               st.session_state.user_name, fb, tt, doc]
                        sheet_ungvien.append_row(row)
                        
                        if upload_status == "FAIL":
                            st.warning("⚠️ Đã lưu thông tin, NHƯNG không upload được ảnh do lỗi Google (Quota). Bạn hãy dùng link ảnh thay thế lần sau.")
                        else:
                            st.success("✅ Đã lưu thành công!")
                        time.sleep(2); st.rerun()
                else: st.error("Thiếu thông tin bắt buộc!")

    # --- PAGE: DANH SÁCH ---
    elif st.session_state.current_page == "list":
        st.header("🔍 Tra Cứu Hồ Sơ")
        if not df.empty:
            search = st.text_input("🔎 Tìm kiếm (Tên, SĐT, CCCD):")
            df_show = df
            if search: df_show = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
            st.dataframe(df_show[['HoTen', 'NamSinh', 'SDT', 'ViTri', 'TrangThai']], use_container_width=True, hide_index=True)
            for i, row in df_show.iterrows():
                with st.expander(f"👤 {row['HoTen']} - {row['TrangThai']}"):
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        if row.get('LinkAnh') and row['LinkAnh'].startswith('http'): 
                            st.image(row['LinkAnh'], width=100)
                        else: st.info("Không có ảnh")
                        st.image(generate_qr(row['HoTen']), width=80)
                    with c2:
                        st.write(f"📞 {row['SDT']} | 🆔 {row.get('CCCD')}")
                        st.write(f"🏠 {row['QueQuan']}")
                        if row.get('LinkFB'): st.markdown(f"🌐 [Facebook]({row['LinkFB']})")

    # --- PAGE: MẪU BÀI ĐĂNG (KHÔI PHỤC) ---
    elif st.session_state.current_page == "templates":
        st.header("📋 Kho Mẫu Bài Đăng (Copy nhanh)")
        if sheet_templates:
            with st.expander("➕ Thêm mẫu mới"):
                with st.form("new_tpl"):
                    tt = st.text_input("Tiêu đề"); ct = st.text_area("Nội dung")
                    if st.form_submit_button("Lưu mẫu"):
                        sheet_templates.append_row([tt, ct, datetime.now().strftime("%d/%m/%Y")])
                        st.success("Đã lưu!"); st.rerun()
            
            st.markdown("---")
            data = sheet_templates.get_all_records()
            if data:
                for d in data:
                    with st.container(border=True):
                        st.subheader(f"📌 {d['TieuDe']}")
                        st.markdown(f"<div class='copy-box'>{d['NoiDung']}</div>", unsafe_allow_html=True)
                        st.caption("Mẹo: Bôi đen nội dung trên để copy.")
            else: st.info("Chưa có mẫu nào.")
        else: st.warning("Chưa tạo Sheet 'MauBai'. Hãy tạo sheet này trên Excel để dùng tính năng.")

    # --- PAGE: KHO ẢNH (NẾU CÓ) ---
    elif st.session_state.current_page == "storage" and sheet_storage:
        st.header("📂 Kho Ảnh Marketing")
        with st.form("up_img"):
            f = st.file_uploader("Upload ảnh lên (Có thể lỗi nếu Google chặn)"); t = st.text_input("Tên ảnh"); n = st.text_area("Ghi chú")
            if st.form_submit_button("Lưu ảnh"):
                res = upload_to_drive(f, f"MKT_{t}.jpg")
                if res == "ERROR_QUOTA": st.error("Google chặn upload do hết dung lượng Bot. Hãy dùng link ảnh ngoài.")
                elif res: 
                    sheet_storage.append_row([datetime.now().strftime("%d/%m/%Y"), t, res, n])
                    st.success("OK!"); st.rerun()
        
        # Hiển thị ảnh
        data = sheet_storage.get_all_records()
        if data:
            cols = st.columns(3)
            for idx, d in enumerate(data):
                with cols[idx%3]:
                    if d.get('LinkAnh'): st.image(d['LinkAnh'], use_container_width=True)
                    st.caption(d['TenAnh'])

    # --- PAGE: ADMIN ---
    elif st.session_state.current_page == "admin":
        st.header("⚙️ Quản Trị")
        users = sheet_users.get_all_records()
        st.dataframe(users)
        with st.form("role"):
            u = st.selectbox("User", [x['Username'] for x in users]); r = st.selectbox("Role", ["staff", "admin"])
            if st.form_submit_button("Cập nhật"):
                cell = sheet_users.find(u); sheet_users.update_cell(cell.row, 3, r)
                st.success("Done!"); st.rerun()

# --- RUN ---
if st.session_state.logged_in: main_app()
else: login_screen()
