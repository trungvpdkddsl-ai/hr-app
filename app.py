import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
from datetime import datetime, date
import qrcode
from io import BytesIO
import requests
import base64

# --- THƯ VIỆN XỬ LÝ WORD ---
try:
    from docx import Document
    from docx.shared import Pt
except ImportError:
    st.error("Chưa cài thư viện python-docx. Vui lòng chạy: pip install python-docx")
    st.stop()

# --- CẤU HÌNH ---
st.set_page_config(page_title="HR System Pro", layout="wide", page_icon="💎")

# Link Apps Script (Giữ nguyên của bạn)
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzKueqCnPonJ1MsFzQpQDk7ihgnVVQyNHMUyc_dx6AocsDu1jW1zf6Gr9VgqMD4D00/exec"

# --- CSS GIAO DIỆN ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {background-color: #f8f9fa;}
    [data-testid="stSidebar"] .stButton > button {
        width: 100%; height: 50px; border: none; border-radius: 8px;
        background-color: white; color: #333; font-weight: 600;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: left; padding-left: 15px; margin-bottom: 5px;
    }
    [data-testid="stSidebar"] .stButton > button:hover {background-color: #e3f2fd; color: #1565c0;}
    
    /* Style cho link tải ảnh */
    .download-link {
        display: inline-block; padding: 5px 10px; background-color: #4CAF50; color: white !important; 
        text-decoration: none; border-radius: 4px; font-size: 12px; margin-top: 5px;
    }
    .download-link:hover {background-color: #45a049;}
    </style>
""", unsafe_allow_html=True)

# --- KẾT NỐI ---
@st.cache_resource
def get_gcp_service():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        return client
    except: return None

client = get_gcp_service()
if not client: st.error("⚠️ Lỗi kết nối Secrets!"); st.stop()

# MỞ SHEET
try:
    sheet_ungvien = client.open("TuyenDungKCN_Data").worksheet("UngVien")
    sheet_users = client.open("TuyenDungKCN_Data").worksheet("Users")
except: st.error("⚠️ Không tìm thấy file Excel hoặc Sheet UngVien/Users."); st.stop()

# --- CÁC HÀM HỖ TRỢ ---
def upload_via_appsscript(file_obj, file_name):
    try:
        file_bytes = file_obj.getvalue()
        base64_str = base64.b64encode(file_bytes).decode('utf-8')
        payload = {"base64": base64_str, "filename": file_name, "mimeType": file_obj.type}
        response = requests.post(APPS_SCRIPT_URL, json=payload)
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("result") == "success": return res_json.get("link")
    except: pass
    return None

def convert_drive_link(link):
    if "id=" in link:
        file_id = link.split("id=")[1]
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000" 
    return link

# --- HÀM TẠO FILE WORD ---
def create_word_file(data):
    doc = Document()
    
    # Tiêu đề
    head = doc.add_heading(f"HỒ SƠ ỨNG VIÊN: {data['HoTen']}", 0)
    head.alignment = 1 # Center

    # Thông tin cơ bản
    doc.add_paragraph(f"Vị trí ứng tuyển: {data['ViTri']}")
    doc.add_paragraph(f"Trạng thái hiện tại: {data['TrangThai']}")
    
    # I. Thông tin cá nhân
    doc.add_heading('I. THÔNG TIN CÁ NHÂN', level=1)
    p = doc.add_paragraph()
    p.add_run("Họ và tên: ").bold = True; p.add_run(f"{data['HoTen']}\n")
    p.add_run("Ngày sinh: ").bold = True; p.add_run(f"{data['NamSinh']}\n")
    p.add_run("Số điện thoại: ").bold = True; p.add_run(f"{data['SDT']}\n")
    p.add_run("CCCD: ").bold = True; p.add_run(f"{data.get('CCCD', '')}\n")
    p.add_run("Quê quán: ").bold = True; p.add_run(f"{data['QueQuan']}")

    # II. Thông tin bổ sung
    doc.add_heading('II. THÔNG TIN BỔ SUNG', level=1)
    p2 = doc.add_paragraph()
    p2.add_run(f"Nguồn tuyển dụng: {data.get('Nguồn', '')}\n")
    p2.add_run(f"Đăng ký xe tuyến: {data.get('XeTuyen', '')}\n")
    p2.add_run(f"Nhu cầu KTX: {data.get('KTX', '')}\n")
    p2.add_run(f"Tình trạng giấy tờ: {data.get('GiayTo', '')}")

    # Footer
    doc.add_paragraph(f"\nNgày xuất hồ sơ: {datetime.now().strftime('%d/%m/%Y')}")

    # Lưu vào buffer
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- SESSION ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_page' not in st.session_state: st.session_state.current_page = "dashboard"
def set_page(page_name): st.session_state.current_page = page_name

# --- LOGIN ---
def login_screen():
    st.markdown("<br><h1 style='text-align: center; color:#1565c0'>🔐 HR SYSTEM PRO</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        tab1, tab2 = st.tabs(["ĐĂNG NHẬP", "ĐĂNG KÝ"])
        with tab1:
            with st.form("login"):
                u = st.text_input("Username"); p = st.text_input("Password", type="password")
                if st.form_submit_button("VÀO HỆ THỐNG", use_container_width=True):
                    users = sheet_users.get_all_records()
                    found = False
                    for user in users:
                        if str(user['Username']) == u and str(user['Password']) == p:
                            st.session_state.logged_in = True; st.session_state.user_role = user['Role']
                            st.session_state.user_name = user['HoTen']; found = True; st.rerun()
                    if not found: st.error("Sai thông tin!")
        with tab2:
            with st.form("reg"):
                nu = st.text_input("User mới"); np = st.text_input("Pass mới", type="password"); nn = st.text_input("Họ tên")
                if st.form_submit_button("TẠO TÀI KHOẢN", use_container_width=True):
                    existing = sheet_users.col_values(1)
                    if nu in existing: st.warning("Tên tồn tại!")
                    else: sheet_users.append_row([nu, np, "staff", nn]); st.success("OK! Mời đăng nhập.")

# --- MAIN APP ---
def main_app():
    df = pd.DataFrame(sheet_ungvien.get_all_records())

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"Role: {st.session_state.user_role.upper()}")
        st.markdown("---")
        if st.button("🏠 DASHBOARD"): set_page("dashboard")
        if st.button("📝 NHẬP HỒ SƠ"): set_page("input")
        if st.button("🔍 DANH SÁCH"): set_page("list")
        
        if st.session_state.user_role == "admin":
            st.markdown("---"); 
            if st.button("⚙️ QUẢN TRỊ"): set_page("admin")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất"): st.session_state.logged_in = False; st.rerun()

    # 1. DASHBOARD
    if st.session_state.current_page == "dashboard":
        st.title("📊 Tổng Quan")
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Tổng Hồ Sơ", len(df))
            with c2: st.metric("Đã Đi Làm", len(df[df['TrangThai']=='Đã đi làm']))
            with c3: st.metric("Mới Nhận", len(df[df['TrangThai']=='Mới nhận']))
            st.markdown("---")
            c4, c5 = st.columns([2, 1])
            with c4: 
                st.subheader("🏆 Top Tuyển Dụng")
                if 'NguoiTuyen' in df.columns: st.bar_chart(df['NguoiTuyen'].value_counts())
            with c5: 
                st.subheader("🎯 Nguồn"); st.dataframe(df['Nguồn'].value_counts(), use_container_width=True)

    # 2. NHẬP LIỆU
    elif st.session_state.current_page == "input":
        st.header("📝 Nhập Hồ Sơ")
        with st.form("input_form"):
            col_img, col_info = st.columns([1, 3])
            with col_img:
                uploaded_file = st.file_uploader("Upload ảnh (3x4)", type=['jpg','png','jpeg'])
            with col_info:
                name = st.text_input("Họ tên (*)")
                phone = st.text_input("SĐT (*)")
                cccd = st.text_input("CCCD") # Không bắt buộc

            r1, r2, r3 = st.columns(3)
            dob = r1.date_input("Ngày sinh", value=date(2000, 1, 1), min_value=date(1960, 1, 1))
            hometown = r2.text_input("Quê quán")
            pos = r3.selectbox("Vị trí", ["Công nhân", "Kỹ thuật", "Kho", "Bảo vệ", "Tạp vụ", "Khác"])
            
            r4, r5 = st.columns(2)
            source = r4.selectbox("Nguồn", ["Facebook", "Zalo", "Trực tiếp"])
            img_link_backup = r5.text_input("Link ảnh dự phòng (Nếu không upload)")

            st.markdown("---")
            fb = st.text_input("Link Facebook"); tt = st.text_input("Link TikTok")
            r6, r7, r8 = st.columns(3)
            bus = r6.selectbox("Xe tuyến", ["Tự túc", "Tuyến A", "Tuyến B"])
            doc = r7.selectbox("Giấy tờ", ["Chưa có", "Đủ giấy tờ"])
            ktx = r8.selectbox("Ký túc xá", ["Không", "Có"])

            if st.form_submit_button("LƯU HỒ SƠ", type="primary"):
                if name and phone: 
                    with st.spinner("Đang xử lý ảnh..."):
                        final_link = img_link_backup 
                        if uploaded_file:
                            link_drive = upload_via_appsscript(uploaded_file, f"{name}_{phone}.jpg")
                            if link_drive: final_link = link_drive
                        
                        row = [datetime.now().strftime("%d/%m/%Y"), name.upper(), dob.strftime("%d/%m/%Y"), hometown, 
                               f"'{phone}", f"'{cccd}", pos, "Mới nhận", "", source, final_link, bus, ktx, 
                               st.session_state.user_name, fb, tt, doc]
                        sheet_ungvien.append_row(row)
                        st.success("✅ Thành công!"); time.sleep(1); st.rerun()
                else: st.error("Vui lòng nhập Tên và SĐT!")

    # 3. DANH SÁCH (TÍNH NĂNG CAO CẤP: SỬA + XUẤT WORD)
    elif st.session_state.current_page == "list":
        st.header("🔍 Tra Cứu & Quản Lý Hồ Sơ")
        
        # Nút reload để cập nhật dữ liệu mới nhất
        if st.button("🔄 Làm mới dữ liệu", type="secondary"):
            st.cache_data.clear()
            st.rerun()

        if not df.empty:
            search = st.text_input("🔎 Tìm kiếm (Tên, SĐT...):")
            # Filter
            df_show = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else df
            
            # Overview Table
            st.dataframe(df_show[['HoTen', 'SDT', 'ViTri', 'TrangThai']], use_container_width=True, hide_index=True)
            
            st.write("---")
            st.write(f"### 📂 Chi tiết hồ sơ ({len(df_show)} kết quả):")

            for i, row in df_show.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1.5, 3.5, 1.5])
                    
                    # 1. Ảnh
                    with c1:
                        raw_link = str(row.get('LinkAnh', ''))
                        if raw_link and raw_link.startswith('http'):
                            thumb_link = convert_drive_link(raw_link)
                            st.image(thumb_link, width=150)
                        else:
                            st.info("Chưa có ảnh")

                    # 2. Thông tin
                    with c2:
                        st.subheader(f"{row['HoTen']} ({row['NamSinh']})")
                        st.write(f"📞 **{row['SDT']}**")
                        st.write(f"🆔 CCCD: {row.get('CCCD', '---')}")
                        st.write(f"🏠 Quê quán: {row['QueQuan']}")
                        st.write(f"💼 Vị trí: {row['ViTri']} | Trạng thái: **{row['TrangThai']}**")
                    
                    # 3. Hành động
                    with c3:
                        st.write("🔧 **Thao tác**")
                        
                        # >> NÚT XUẤT WORD
                        doc_file = create_word_file(row)
                        st.download_button(
                            label="📄 Xuất Word",
                            data=doc_file,
                            file_name=f"HoSo_{row['HoTen']}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_{i}",
                            use_container_width=True
                        )

                    # >> FORM CHỈNH SỬA
                    with st.expander(f"✏️ Chỉnh sửa thông tin: {row['HoTen']}"):
                        with st.form(key=f"edit_form_{i}"):
                            e_c1, e_c2 = st.columns(2)
                            new_name = e_c1.text_input("Họ tên", value=row['HoTen'])
                            # Xử lý CCCD để bỏ dấu ' nếu có khi hiển thị
                            current_cccd = str(row.get('CCCD','')).replace("'","")
                            new_cccd = e_c2.text_input("CCCD", value=current_cccd)
                            
                            e_c3, e_c4 = st.columns(2)
                            new_hometown = e_c3.text_input("Quê quán", value=row['QueQuan'])
                            
                            # Xử lý Selectbox
                            list_pos = ["Công nhân", "Kỹ thuật", "Kho", "Bảo vệ", "Tạp vụ", "Khác"]
                            idx_pos = list_pos.index(row['ViTri']) if row['ViTri'] in list_pos else 0
                            new_pos = e_c4.selectbox("Vị trí", list_pos, index=idx_pos)
                            
                            list_status = ["Mới nhận", "Phỏng vấn", "Đạt", "Đã đi làm", "Loại", "Nghỉ việc"]
                            idx_status = list_status.index(row['TrangThai']) if row['TrangThai'] in list_status else 0
                            new_status = st.selectbox("Trạng thái", list_status, index=idx_status)
                            
                            if st.form_submit_button("💾 CẬP NHẬT LẠI"):
                                try:
                                    # Tìm dòng dựa vào SĐT
                                    cell = sheet_ungvien.find(str(row['SDT']))
                                    if cell:
                                        # Cập nhật các cột tương ứng (Dựa trên cấu trúc mảng row lúc nhập liệu)
                                        sheet_ungvien.update_cell(cell.row, 2, new_name.upper()) # Cột 2: Tên
                                        sheet_ungvien.update_cell(cell.row, 4, new_hometown)     # Cột 4: Quê
                                        sheet_ungvien.update_cell(cell.row, 6, f"'{new_cccd}")   # Cột 6: CCCD (Thêm ' để không mất số 0)
                                        sheet_ungvien.update_cell(cell.row, 7, new_pos)          # Cột 7: Vị trí
                                        sheet_ungvien.update_cell(cell.row, 8, new_status)       # Cột 8: Trạng thái
                                        
                                        st.success("✅ Đã cập nhật xong! Bấm 'Làm mới dữ liệu' để xem kết quả.")
                                    else:
                                        st.error("⚠️ Không tìm thấy SĐT trong dữ liệu gốc.")
                                except Exception as e:
                                    st.error(f"Lỗi khi lưu: {e}")

    # 6. ADMIN
    elif st.session_state.current_page == "admin":
        st.header("⚙️ Admin"); users = sheet_users.get_all_records(); st.dataframe(users)
        with st.form("rl"):
            u = st.selectbox("User", [x['Username'] for x in users]); r = st.selectbox("Role", ["staff", "admin"])
            if st.form_submit_button("Update"): cell = sheet_users.find(u); sheet_users.update_cell(cell.row, 3, r); st.success("Done!"); st.rerun()

# --- RUN ---
if st.session_state.logged_in: main_app()
else: login_screen()
