import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
from datetime import datetime, date
import requests
import base64
from io import BytesIO

# --- KIỂM TRA THƯ VIỆN WORD ---
try:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    st.error("⚠️ Lỗi: Chưa cài thư viện python-docx. Vui lòng chạy lệnh: pip install python-docx")
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

# --- KẾT NỐI GOOGLE SHEETS ---
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

# --- HÀM XUẤT WORD (CHUẨN FONT TIMES NEW ROMAN) ---
def create_word_file(data):
    doc = Document()
    
    # Cấu hình Font mặc định
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(13)

    # Tiêu đề
    head = doc.add_heading(f"HỒ SƠ ỨNG VIÊN: {data['HoTen']}", 0)
    head.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in head.runs:
        run.font.name = 'Times New Roman'
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0) # Màu đen

    # Hàm phụ trợ để thêm dòng
    def add_line(label, value):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        runner = p.add_run(f"{label}: ")
        runner.font.name = 'Times New Roman'
        runner.font.bold = True
        
        val_str = str(value) if value else ""
        runner_val = p.add_run(val_str)
        runner_val.font.name = 'Times New Roman'

    # Thông tin tóm tắt
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run(f"(Vị trí: {data['ViTri']} | Trạng thái: {data['TrangThai']})")
    run_sub.font.name = 'Times New Roman'
    run_sub.italic = True
    
    doc.add_paragraph("") # Dòng trống

    # I. THÔNG TIN CÁ NHÂN
    h1 = doc.add_heading('I. THÔNG TIN CÁ NHÂN', level=1)
    for run in h1.runs:
        run.font.name = 'Times New Roman'; run.font.size = Pt(14); run.font.color.rgb = RGBColor(0,0,0)

    add_line("Họ và tên", data['HoTen'])
    add_line("Ngày sinh", data['NamSinh'])
    add_line("Số điện thoại", data['SDT'])
    add_line("CCCD", data.get('CCCD', ''))
    add_line("Quê quán", data['QueQuan'])

    # II. THÔNG TIN KHÁC
    h2 = doc.add_heading('II. THÔNG TIN KHÁC', level=1)
    for run in h2.runs:
        run.font.name = 'Times New Roman'; run.font.size = Pt(14); run.font.color.rgb = RGBColor(0,0,0)

    # Xử lý an toàn nếu thiếu cột
    nguon = data.get('Nguồn', data.get('Nguon', ''))
    xe = data.get('XeTuyen', '')
    ktx = data.get('KTX', '')
    giayto = data.get('GiayTo', '')

    add_line("Nguồn tuyển dụng", nguon)
    add_line("Đăng ký xe tuyến", xe)
    add_line("Nhu cầu KTX", ktx)
    add_line("Tình trạng giấy tờ", giayto)

    # Footer
    doc.add_paragraph("")
    p_footer = doc.add_paragraph(f"Ngày xuất hồ sơ: {datetime.now().strftime('%d/%m/%Y')}")
    p_footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in p_footer.runs:
        run.font.name = 'Times New Roman'; run.font.italic = True; run.font.size = Pt(11)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- SESSION ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_page' not in st.session_state: st.session_state.current_page = "dashboard"
def set_page(page_name): st.session_state.current_page = page_name

# --- LOGIN SCREEN ---
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
    # Lấy dữ liệu và làm sạch tên cột (bỏ khoảng trắng thừa nếu có)
    raw_data = sheet_ungvien.get_all_records()
    df = pd.DataFrame(raw_data)
    # Chuẩn hóa tên cột để tránh lỗi
    df.columns = [c.strip() for c in df.columns]

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

    # 1. DASHBOARD (ĐÃ SỬA LỖI & ĐỔI GIAO DIỆN)
    if st.session_state.current_page == "dashboard":
        st.title("📊 Tổng Quan")
        if not df.empty:
            # Metrics
            c1, c2, c3 = st.columns(3)
            # Kiểm tra cột TrangThai tồn tại không
            tt_col = 'TrangThai' if 'TrangThai' in df.columns else None
            
            da_di_lam = len(df[df[tt_col]=='Đã đi làm']) if tt_col else 0
            moi_nhan = len(df[df[tt_col]=='Mới nhận']) if tt_col else 0
            
            with c1: st.metric("Tổng Hồ Sơ", len(df))
            with c2: st.metric("Đã Đi Làm", da_di_lam)
            with c3: st.metric("Mới Nhận", moi_nhan)
            
            st.markdown("---")
            c4, c5 = st.columns([2, 1])
            
            # --- CẬP NHẬT: HIỂN THỊ DẠNG BẢNG THAY VÌ BIỂU ĐỒ ---
            with c4: 
                st.subheader("🏆 Top Tuyển Dụng")
                if 'NguoiTuyen' in df.columns:
                    # Tạo bảng thống kê
                    top_recruiter = df['NguoiTuyen'].value_counts().reset_index()
                    top_recruiter.columns = ['Người Tuyển', 'Số Lượng Hồ Sơ'] # Đổi tên cột hiển thị
                    st.dataframe(top_recruiter, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ Không tìm thấy cột 'NguoiTuyen' trong dữ liệu.")

            # --- CẬP NHẬT: SỬA LỖI KEYERROR 'NGUỒN' ---
            with c5: 
                st.subheader("🎯 Nguồn")
                # Tìm cột Nguồn (có dấu hoặc không dấu)
                col_nguon = None
                if 'Nguồn' in df.columns: col_nguon = 'Nguồn'
                elif 'Nguon' in df.columns: col_nguon = 'Nguon'
                
                if col_nguon:
                    st.dataframe(df[col_nguon].value_counts(), use_container_width=True)
                else:
                    st.info("⚠️ Không tìm thấy cột 'Nguồn'")

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

    # 3. DANH SÁCH (TRA CỨU + SỬA + WORD)
    elif st.session_state.current_page == "list":
        st.header("🔍 Tra Cứu & Quản Lý Hồ Sơ")
        
        if st.button("🔄 Làm mới dữ liệu", type="secondary"):
            st.cache_data.clear()
            st.rerun()

        if not df.empty:
            search = st.text_input("🔎 Tìm kiếm (Tên, SĐT...):")
            df_show = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else df
            
            # Overview Table
            st.dataframe(df_show[['HoTen', 'SDT', 'ViTri', 'TrangThai']], use_container_width=True, hide_index=True)
            
            st.write("---")
            st.write(f"### 📂 Chi tiết ({len(df_show)} hồ sơ):")

            for i, row in df_show.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1.5, 3.5, 1.5])
                    
                    # 1. Ảnh
                    with c1:
                        raw_link = str(row.get('LinkAnh', ''))
                        if raw_link and raw_link.startswith('http'):
                            thumb_link = convert_drive_link(raw_link)
                            st.image(thumb_link, width=150)
                        else: st.info("No Image")

                    # 2. Thông tin
                    with c2:
                        st.subheader(f"{row['HoTen']} ({row['NamSinh']})")
                        st.write(f"📞 **{row['SDT']}**")
                        # Xử lý hiển thị CCCD an toàn
                        cccd_val = row.get('CCCD', '---')
                        st.write(f"🆔 CCCD: {cccd_val}")
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
                    with st.expander(f"✏️ Chỉnh sửa: {row['HoTen']}"):
                        with st.form(key=f"edit_form_{i}"):
                            e_c1, e_c2 = st.columns(2)
                            new_name = e_c1.text_input("Họ tên", value=row['HoTen'])
                            
                            # Xử lý CCCD để bỏ dấu ' nếu có
                            current_cccd = str(row.get('CCCD','')).replace("'","")
                            new_cccd = e_c2.text_input("CCCD", value=current_cccd)
                            
                            e_c3, e_c4 = st.columns(2)
                            new_hometown = e_c3.text_input("Quê quán", value=row['QueQuan'])
                            
                            # Selectbox an toàn
                            list_pos = ["Công nhân", "Kỹ thuật", "Kho", "Bảo vệ", "Tạp vụ", "Khác"]
                            val_pos = row['ViTri'] if row['ViTri'] in list_pos else list_pos[0]
                            new_pos = e_c4.selectbox("Vị trí", list_pos, index=list_pos.index(val_pos))
                            
                            list_status = ["Mới nhận", "Phỏng vấn", "Đạt", "Đã đi làm", "Loại", "Nghỉ việc"]
                            val_stt = row['TrangThai'] if row['TrangThai'] in list_status else list_status[0]
                            new_status = st.selectbox("Trạng thái", list_status, index=list_status.index(val_stt))
                            
                            if st.form_submit_button("💾 CẬP NHẬT LẠI"):
                                try:
                                    # Tìm dòng dựa vào SĐT (Unique Key)
                                    cell = sheet_ungvien.find(str(row['SDT']))
                                    if cell:
                                        # Update các cột tương ứng (Cần map đúng cột trong Excel của bạn)
                                        # Giả định thứ tự: [Ngay, HoTen, NamSinh, QueQuan, SDT, CCCD, ViTri, TrangThai...]
                                        sheet_ungvien.update_cell(cell.row, 2, new_name.upper()) # Col 2: HoTen
                                        sheet_ungvien.update_cell(cell.row, 4, new_hometown)     # Col 4: QueQuan
                                        sheet_ungvien.update_cell(cell.row, 6, f"'{new_cccd}")   # Col 6: CCCD
                                        sheet_ungvien.update_cell(cell.row, 7, new_pos)          # Col 7: ViTri
                                        sheet_ungvien.update_cell(cell.row, 8, new_status)       # Col 8: TrangThai
                                        st.success("✅ Đã cập nhật xong! Bấm 'Làm mới' để xem.")
                                    else: st.error("⚠️ Không tìm thấy SĐT trong file gốc.")
                                except Exception as e: st.error(f"Lỗi: {e}")

    # 4. ADMIN
    elif st.session_state.current_page == "admin":
        st.header("⚙️ Admin"); users = sheet_users.get_all_records(); st.dataframe(users)
        with st.form("rl"):
            u = st.selectbox("User", [x['Username'] for x in users]); r = st.selectbox("Role", ["staff", "admin"])
            if st.form_submit_button("Update"): cell = sheet_users.find(u); sheet_users.update_cell(cell.row, 3, r); st.success("Done!"); st.rerun()

# --- RUN ---
if st.session_state.logged_in: main_app()
else: login_screen()
