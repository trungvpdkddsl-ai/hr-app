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
st.set_page_config(page_title="HR KCN Smart Social", layout="wide", page_icon="🏭")

# --- CẤU HÌNH ID DRIVE ---
FOLDER_ID_DRIVE = "1Sw91t5o-m8fwZsbGpJw8Yex_WzV8etCx"

# --- CSS GIAO DIỆN ---
st.markdown("""
    <style>
    /* Nút Zalo, FB, TikTok */
    .social-btn {
        display: inline-block;
        padding: 5px 10px;
        text-decoration: none;
        border-radius: 5px;
        font-weight: bold;
        color: white !important;
        margin-right: 5px;
        font-size: 12px;
    }
    .zalo {background-color: #0068FF;}
    .fb {background-color: #1877F2;}
    .tiktok {background-color: #000000;}
    
    /* Box tính lương */
    .salary-box {
        background-color: #e3f2fd;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #90caf9;
    }
    .final-salary {
        font-size: 24px;
        color: #d32f2f;
        font-weight: bold;
        text-align: center;
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

# --- LOGIN SCREEN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = None

def login_screen():
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown("<h2 style='text-align: center;'>🏭 HR SOCIAL APP</h2>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Đăng Nhập", "Đăng Ký"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Vào hệ thống", use_container_width=True):
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
                if st.form_submit_button("Đăng ký"):
                    sheet_users.append_row([nu, np, "staff", nn])
                    st.success("Tạo xong!")

# --- MAIN APP ---
def main_app():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"Vai trò: {st.session_state.user_role}")
        menu = st.radio("MENU", ["🏠 Trang Chủ", "📝 Nhập Hồ Sơ", "📋 Danh Sách", "🖩 Tính Lương Nhanh"])
        st.markdown("---")
        if st.button("Đăng xuất"): st.session_state.logged_in = False; st.rerun()

    # TẢI DỮ LIỆU
    df = pd.DataFrame(sheet_ungvien.get_all_records())

    # 1. TRANG CHỦ
    if "Trang Chủ" in menu:
        st.title("🚀 Tổng Quan")
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng hồ sơ", len(df))
            c2.metric("Hồ sơ đủ giấy tờ", len(df[df['TrangThaiHoSo'] == 'Đủ giấy tờ']))
            c3.metric("Tỉ lệ có TikTok", f"{len(df[df['LinkTikTok'] != '']) / len(df) * 100:.0f}%")
            
            st.markdown("---")
            st.subheader("Hiệu quả nguồn tuyển dụng")
            st.bar_chart(df['Nguồn'].value_counts())

    # 2. NHẬP HỒ SƠ (CÓ FB/TIKTOK)
    elif "Nhập Hồ Sơ" in menu:
        st.header("📝 Nhập Hồ Sơ Mới")
        with st.form("input_social"):
            c1, c2 = st.columns([1, 2])
            with c1:
                uploaded_file = st.file_uploader("Ảnh 3x4", type=['jpg','png'])
                if uploaded_file: st.image(uploaded_file, width=130)
            with c2:
                name = st.text_input("Họ tên (*)")
                phone = st.text_input("SĐT (*)")
                cccd = st.text_input("CCCD (*)")
            
            st.markdown("---")
            st.markdown("###### 🌐 Thông tin Mạng Xã Hội (Để check thái độ ứng viên)")
            s1, s2 = st.columns(2)
            fb = s1.text_input("Link Facebook")
            tt = s2.text_input("Link TikTok")
            
            st.markdown("###### 💼 Thông tin Ứng Tuyển")
            r1, r2, r3 = st.columns(3)
            pos = r1.selectbox("Vị trí", ["Công nhân", "Kỹ thuật", "Kho", "Bảo vệ"])
            source = r2.selectbox("Nguồn", ["Facebook", "TikTok", "Zalo", "Giới thiệu"])
            status_doc = r3.selectbox("Tình trạng giấy tờ", ["Chưa có gì", "Thiếu khám SK", "Thiếu SYLL", "Đủ giấy tờ"])
            
            note = st.text_area("Ghi chú")
            
            if st.form_submit_button("LƯU HỒ SƠ", type="primary"):
                if not name or not phone:
                    st.error("Thiếu Tên hoặc SĐT!")
                else:
                    with st.spinner("Đang lưu..."):
                        link = upload_to_drive(uploaded_file, f"{name}_{phone}.jpg") if uploaded_file else ""
                        row = [
                            datetime.now().strftime("%d/%m/%Y"), name.upper(), "", "", f"'{phone}", f"'{cccd}",
                            pos, "Mới nhận", note, source, link, "Tự túc", "Không", 
                            st.session_state.user_name, fb, tt, status_doc
                        ]
                        sheet_ungvien.append_row(row)
                        st.success("✅ Đã lưu!")
                        time.sleep(1)
                        st.rerun()

    # 3. DANH SÁCH & QR CODE
    elif "Danh Sách" in menu:
        st.header("📋 Danh Sách Ứng Viên")
        search = st.text_input("🔍 Tìm kiếm tên, SĐT...")
        
        if not df.empty:
            if search:
                df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            
            for i, row in df.iterrows():
                with st.expander(f"👤 {row['HoTen']} - {row['ViTri']}"):
                    c1, c2, c3 = st.columns([1, 2, 1])
                    with c1:
                        if row.get('LinkAnh'): st.image(row['LinkAnh'], width=100)
                        
                        # Hiển thị QR Code
                        st.write("---")
                        qr_data = f"Họ tên: {row['HoTen']}\nSĐT: {row['SDT']}\nCCCD: {row.get('CCCD','')}\nVị trí: {row['ViTri']}"
                        st.image(generate_qr(qr_data), caption="Mã hồ sơ", width=100)

                    with c2:
                        st.write(f"📞 **SĐT:** {row['SDT']}")
                        st.write(f"📂 **Giấy tờ:** {row.get('TrangThaiHoSo', 'Chưa cập nhật')}")
                        st.write(f"ℹ️ **Nguồn:** {row.get('Nguồn', '')}")
                        st.info(f"Note: {row.get('GhiChu', '')}")

                    with c3:
                        st.write("🔗 **Kết nối:**")
                        zalo = format_zalo_link(row['SDT'])
                        st.markdown(f'<a href="{zalo}" target="_blank" class="social-btn zalo">Zalo Chat</a>', unsafe_allow_html=True)
                        
                        if row.get('LinkFB'):
                            st.markdown(f'<a href="{row["LinkFB"]}" target="_blank" class="social-btn fb">Facebook</a>', unsafe_allow_html=True)
                        if row.get('LinkTikTok'):
                            st.markdown(f'<a href="{row["LinkTikTok"]}" target="_blank" class="social-btn tiktok">TikTok</a>', unsafe_allow_html=True)

    # 4. TÍNH LƯƠNG NHANH (MỚI)
    elif "Tính Lương" in menu:
        st.header("🖩 Ước Tính Lương (Để tư vấn)")
        st.markdown("Sử dụng công cụ này để cho ứng viên thấy thu nhập dự kiến của họ.")
        
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                base_salary = st.number_input("Lương cơ bản (VND)", value=4500000, step=100000)
                allowance = st.number_input("Tổng phụ cấp (Ăn, Đi lại...)", value=1200000, step=50000)
            with col2:
                ot_hours = st.number_input("Số giờ tăng ca (OT) dự kiến", value=40)
                ot_rate = st.number_input("Hệ số lương OT", value=1.5)
            
            if st.button("Tính toán ngay"):
                ot_pay = (base_salary / 26 / 8) * ot_hours * ot_rate
                total = base_salary + allowance + ot_pay
                
                st.markdown("---")
                st.markdown(f"""
                <div class="salary-box">
                    <h3 style="text-align:center; color:#555">THU NHẬP DỰ KIẾN (26 công)</h3>
                    <div class="final-salary">{total:,.0f} VNĐ</div>
                    <p style="text-align:center">Bao gồm: Lương CB + Phụ cấp + {ot_pay:,.0f} tiền OT</p>
                </div>
                """, unsafe_allow_html=True)

# --- RUN ---
if st.session_state.logged_in:
    main_app()
else:
    login_screen()
