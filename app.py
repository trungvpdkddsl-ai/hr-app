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
from PIL import Image

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="HR Pro Ultimate", layout="wide", page_icon="💎")

# --- CẤU HÌNH ID DRIVE ---
FOLDER_ID_DRIVE = "1Sw91t5o-m8fwZsbGpJw8Yex_WzV8etCx"

# --- CSS GIAO DIỆN ---
st.markdown("""
    <style>
    .social-btn {
        display: inline-block; padding: 4px 10px; border-radius: 4px; color: white !important;
        text-decoration: none; font-size: 11px; margin-right: 4px; font-weight: bold;
    }
    .zalo {background-color: #0068FF;}
    .fb {background-color: #1877F2;}
    .tiktok {background-color: #000000;}
    
    .kpi-box {
        background-color: #f0f4c3; padding: 10px; border-radius: 8px; border-left: 5px solid #c0ca33;
    }
    
    .salary-result {
        background-color: #e3f2fd; padding: 20px; border-radius: 10px; 
        text-align: center; font-size: 20px; font-weight: bold; color: #1565c0;
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
    st.error("⚠️ Không tìm thấy Sheet! Hãy kiểm tra lại.")
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

def format_zalo_link(phone):
    p = str(phone).replace("'", "").strip()
    if p.startswith("0"): p = "84" + p[1:]
    return f"https://zalo.me/{p}"

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue()

def check_blacklist(cccd, df):
    if df.empty: return False
    # Kiểm tra nếu CCCD nằm trong danh sách những người có trạng thái 'Vĩnh viễn không tuyển'
    blacklist = df[df['TrangThai'] == "Vĩnh viễn không tuyển"]
    if str(cccd) in blacklist['CCCD'].astype(str).values:
        return True
    return False

# --- LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = None

def login_screen():
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("<h2 style='text-align: center;'>🔐 HR SYSTEM V6</h2>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Đăng Nhập", "Đăng Ký"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Đăng Nhập", use_container_width=True):
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
                nu = st.text_input("User mới"); np = st.text_input("Pass mới", type="password"); nn = st.text_input("Họ tên")
                if st.form_submit_button("Đăng Ký"):
                    sheet_users.append_row([nu, np, "staff", nn])
                    st.success("Tạo thành công!")

# --- MAIN APP ---
def main_app():
    # MENU BÊN TRÁI
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        role_color = "red" if st.session_state.user_role == "admin" else "blue"
        st.markdown(f"Quyền: <b style='color:{role_color}'>{st.session_state.user_role.upper()}</b>", unsafe_allow_html=True)
        
        # Danh sách Menu đầy đủ
        menu_options = [
            "🏠 Trang Chủ", 
            "📝 Nhập Hồ Sơ", 
            "📋 Danh Sách & Social", 
            "📊 Báo Cáo & KPI", 
            "🖩 Tính Lương Nhanh"
        ]
        if st.session_state.user_role == "admin":
            menu_options.append("⚙️ Quản Trị Hệ Thống")
            
        menu = st.radio("CHỨC NĂNG", menu_options)
        
        st.markdown("---")
        if st.button("Đăng xuất"): st.session_state.logged_in = False; st.rerun()

    # LOAD DATA
    df = pd.DataFrame(sheet_ungvien.get_all_records())

    # 1. TRANG CHỦ
    if "Trang Chủ" in menu:
        st.title("🚀 Tổng Quan Hệ Thống")
        if not df.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tổng hồ sơ", len(df))
            c2.metric("Chờ phỏng vấn", len(df[df['TrangThai'] == 'Mới nhận']))
            c3.metric("Có TikTok/FB", len(df[df['LinkTikTok'] != '']) + len(df[df['LinkFB'] != '']))
            c4.metric("Đủ giấy tờ", len(df[df['TrangThaiHoSo'] == 'Đủ giấy tờ']))
            
            st.markdown("---")
            st.info("💡 Mẹo: Dùng menu 'Tính Lương Nhanh' để tư vấn thu nhập cho công nhân mới.")

    # 2. NHẬP HỒ SƠ (ĐẦY ĐỦ 17 CỘT)
    elif "Nhập Hồ Sơ" in menu:
        st.header("📝 Nhập Liệu Toàn Diện")
        with st.form("full_input"):
            c1, c2 = st.columns([1, 2])
            with c1:
                uploaded_file = st.file_uploader("Ảnh chân dung", type=['jpg','png'])
                if uploaded_file: st.image(uploaded_file, width=120)
            with c2:
                name = st.text_input("Họ tên (*)")
                phone = st.text_input("SĐT (*)")
                cccd = st.text_input("CCCD/CMND (*)", help="Hệ thống sẽ check trùng và blacklist")
            
            st.markdown("---")
            col_a, col_b, col_c = st.columns(3)
            yob = col_a.number_input("Năm sinh", 1970, 2010, 2000)
            hometown = col_b.text_input("Quê quán")
            pos = col_c.selectbox("Vị trí", ["Công nhân", "Kỹ thuật", "Kho", "Bảo vệ", "Tạp vụ"])
            
            col_d, col_e, col_f = st.columns(3)
            source = col_d.selectbox("Nguồn", ["Facebook", "Zalo", "TikTok", "Trực tiếp", "Giới thiệu"])
            fb_link = col_e.text_input("Link Facebook")
            tt_link = col_f.text_input("Link TikTok")
            
            col_g, col_h, col_i = st.columns(3)
            bus = col_g.selectbox("Xe tuyến", ["Tự túc", "Tuyến A", "Tuyến B", "Tuyến C"])
            ktx = col_h.selectbox("Ở KTX?", ["Không", "Có đăng ký"])
            doc_status = col_i.selectbox("Giấy tờ", ["Chưa có", "Thiếu khám SK", "Đủ giấy tờ"])
            
            note = st.text_area("Ghi chú phỏng vấn")
            
            if st.form_submit_button("LƯU HỒ SƠ", type="primary"):
                if not name or not phone or not cccd:
                    st.error("Thiếu thông tin bắt buộc (Tên, SĐT, CCCD)")
                elif not df.empty and str(cccd) in df['CCCD'].astype(str).values:
                    st.warning(f"⚠️ Trùng CCCD: {cccd} đã có trong hệ thống!")
                elif check_blacklist(cccd, df):
                    st.error("⛔ CẢNH BÁO: Ứng viên này nằm trong Blacklist!")
                else:
                    with st.spinner("Đang lưu..."):
                        link_img = upload_to_drive(uploaded_file, f"{name}_{cccd}.jpg") if uploaded_file else ""
                        row = [
                            datetime.now().strftime("%d/%m/%Y"), # 1.Ngay
                            name.upper(), yob, hometown, f"'{phone}", f"'{cccd}", # 2-6
                            pos, "Mới nhận", note, source, link_img, # 7-11
                            bus, ktx, st.session_state.user_name, # 12-14
                            fb_link, tt_link, doc_status # 15-17
                        ]
                        sheet_ungvien.append_row(row)
                        st.success("✅ Lưu thành công!")
                        time.sleep(1); st.rerun()

    # 3. DANH SÁCH (CARD VIEW + QR + SOCIAL)
    elif "Danh Sách" in menu:
        st.header("📋 Danh Sách Hồ Sơ")
        search = st.text_input("🔍 Tìm kiếm (Tên, SĐT, CCCD)...")
        
        # Nút xuất Excel
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Tải danh sách Excel", csv, "hr_data.csv", "text/csv")
        
            if search:
                df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
            for i, row in df.iterrows():
                with st.expander(f"👤 {row['HoTen']} - {row['ViTri']}"):
                    c1, c2, c3 = st.columns([1, 2, 1])
                    with c1:
                        if row.get('LinkAnh'): st.image(row['LinkAnh'], width=100)
                        # QR Code
                        qr_info = f"{row['HoTen']}\n{row['SDT']}\n{row.get('CCCD','')}"
                        st.image(generate_qr(qr_info), width=80, caption="Scan Me")
                    with c2:
                        st.write(f"📞 **SĐT:** {row['SDT']} | 🆔 **CCCD:** {row.get('CCCD','')}")
                        st.write(f"🏠 **Quê:** {row['QueQuan']} | 🚌 **Xe:** {row.get('XeTuyen','')}")
                        st.write(f"📂 **Giấy tờ:** {row.get('TrangThaiHoSo','')}")
                        st.info(f"Note: {row.get('GhiChu','')}")
                    with c3:
                        st.write("**Liên hệ & Social:**")
                        zalo = format_zalo_link(row['SDT'])
                        st.markdown(f'<a href="{zalo}" target="_blank" class="social-btn zalo">Chat Zalo</a>', unsafe_allow_html=True)
                        if row.get('LinkFB'):
                            st.markdown(f'<a href="{row["LinkFB"]}" target="_blank" class="social-btn fb">Facebook</a>', unsafe_allow_html=True)
                        if row.get('LinkTikTok'):
                            st.markdown(f'<a href="{row["LinkTikTok"]}" target="_blank" class="social-btn tiktok">TikTok</a>', unsafe_allow_html=True)

    # 4. BÁO CÁO & KPI (ĐÃ KHÔI PHỤC)
    elif "Báo Cáo" in menu:
        st.header("📊 Báo Cáo Hiệu Quả & KPI")
        if df.empty:
            st.info("Chưa có dữ liệu.")
        else:
            tab1, tab2 = st.tabs(["🏆 KPI Nhân Viên", "📈 Biểu Đồ Tổng Quan"])
            
            with tab1:
                st.subheader("Bảng Xếp Hạng Tuyển Dụng")
                if 'NguoiTuyen' in df.columns:
                    kpi = df['NguoiTuyen'].value_counts()
                    st.bar_chart(kpi)
                    st.markdown("""
                        <div class="kpi-box">
                            <b>💡 Ghi chú:</b> Biểu đồ này hiển thị số lượng hồ sơ mỗi nhân viên đã nhập được.
                            Dùng để tính thưởng cuối tháng.
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Dữ liệu chưa có cột Người Tuyển.")

            with tab2:
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Nguồn ứng viên**")
                    st.bar_chart(df['Nguồn'].value_counts())
                with c2:
                    st.write("**Trạng thái phỏng vấn**")
                    st.bar_chart(df['TrangThai'].value_counts())

    # 5. TÍNH LƯƠNG NHANH
    elif "Tính Lương" in menu:
        st.header("🖩 Công Cụ Tính Lương")
        c1, c2 = st.columns(2)
        with c1:
            lcb = st.number_input("Lương cơ bản", value=4500000, step=100000)
            pc = st.number_input("Phụ cấp", value=1000000, step=50000)
        with c2:
            ot = st.number_input("Số giờ tăng ca (h)", value=40)
            hs = st.number_input("Hệ số OT", value=1.5)
            
        if st.button("Tính ngay"):
            tong = lcb + pc + ((lcb/26/8)*ot*hs)
            st.markdown(f"<div class='salary-result'>💰 Tổng thu nhập: {tong:,.0f} VNĐ</div>", unsafe_allow_html=True)

    # 6. QUẢN TRỊ (ĐÃ KHÔI PHỤC)
    elif "Quản Trị" in menu:
        st.header("⚙️ Quản Trị Hệ Thống")
        users = sheet_users.get_all_records()
        st.dataframe(users)
        
        with st.form("admin_role"):
            st.write("Cập nhật quyền hạn nhân viên:")
            u = st.selectbox("Chọn nhân viên", [x['Username'] for x in users])
            r = st.selectbox("Quyền mới", ["staff", "admin"])
            if st.form_submit_button("Cập nhật"):
                cell = sheet_users.find(u)
                sheet_users.update_cell(cell.row, 3, r)
                st.success("Đã xong!")
                time.sleep(1); st.rerun()

# --- RUN ---
if st.session_state.logged_in:
    main_app()
else:
    login_screen()
