import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ Thống Tuyển Dụng KCN", layout="wide", page_icon="🏭")

# --- KẾT NỐI GOOGLE SHEETS ---
@st.cache_resource
def connect_to_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        client = gspread.authorize(creds)
        sheet = client.open("TuyenDungKCN_Data").sheet1 
        return sheet
    except Exception as e:
        return None

sheet = connect_to_gsheet()

# --- CSS TÙY CHỈNH CHO ĐẸP ---
st.markdown("""
    <style>
    .main-header {font-size: 30px; font-weight: bold; color: #2E86C1;}
    .sub-header {font-size: 20px; font-weight: bold; color: #E67E22;}
    .stAlert {padding: 10px; border-radius: 5px;}
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR (MENU TRÁI) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9187/9187555.png", width=80)
    st.markdown("## 🏭 HR MANAGER PRO")
    st.markdown("---")
    
    menu = st.radio(
        "MENU CHỨC NĂNG",
        ["➕ Nhập Hồ Sơ Mới", "📋 Danh Sách & Tìm Kiếm", "📅 Lịch Phỏng Vấn", "📊 Báo Cáo Hiệu Quả"],
    )
    
    st.markdown("---")
    st.caption("Developed by Gemini AI")

# --- HÀM TẢI DỮ LIỆU ---
def load_data():
    if sheet is None:
        return pd.DataFrame()
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = load_data()

# --- KIỂM TRA LỖI KẾT NỐI ---
if sheet is None:
    st.error("⚠️ Lỗi kết nối! Hãy kiểm tra lại phần Secrets trong cài đặt Streamlit.")
    st.stop()

# ==========================================
# CHỨC NĂNG 1: NHẬP HỒ SƠ (ĐÃ NÂNG CẤP)
# ==========================================
if menu == "➕ Nhập Hồ Sơ Mới":
    st.markdown('<p class="main-header">📝 Tiếp Nhận Ứng Viên Mới</p>', unsafe_allow_html=True)
    
    # Kiểm tra trùng lặp
    existing_phones = []
    if not df.empty:
        existing_phones = df['SDT'].astype(str).tolist()

    with st.form("form_add", clear_on_submit=True):
        st.markdown("### 1. Thông tin cá nhân")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            name = st.text_input("Họ và tên (*)", placeholder="Nhập tên đầy đủ (Viết hoa)")
        with c2:
            phone = st.text_input("Số điện thoại (*)", placeholder="Ví dụ: 0988xxxxxx")
        with c3:
            yob = st.number_input("Năm sinh", 1960, 2010, 2000)
            
        st.markdown("### 2. Thông tin ứng tuyển")
        c4, c5, c6 = st.columns(3)
        with c4:
            hometown = st.text_input("Quê quán", placeholder="Huyện, Tỉnh")
        with c5:
            position = st.selectbox("Vị trí ứng tuyển", 
                                    ["Công nhân may", "Lắp ráp điện tử", "Kỹ thuật viên", "QC/KCS", "Kho", "Bảo vệ", "Tạp vụ", "Phiên dịch"])
        with c6:
            source = st.selectbox("Nguồn ứng viên (Họ biết từ đâu?)", 
                                  ["Facebook", "Zalo", "Người quen giới thiệu", "Tờ rơi/Băng rôn", "Trực tiếp tại cổng"])

        st.markdown("### 3. Đánh giá sơ bộ")
        status = st.selectbox("Trạng thái", ["Mới nhận hồ sơ", "Hẹn phỏng vấn", "Đạt - Chờ đi làm", "Không đạt", "Lưu hồ sơ dự phòng"])
        note = st.text_area("Ghi chú chi tiết", placeholder="Kinh nghiệm, thái độ, mức lương mong muốn...")
        
        # Nút bấm lưu
        submitted = st.form_submit_button("💾 LƯU HỒ SƠ")
        
        if submitted:
            # Logic kiểm tra
            if not name or not phone:
                st.error("❌ Vui lòng điền Tên và Số điện thoại!")
            elif phone in existing_phones:
                st.warning(f"⚠️ Cảnh báo: Số điện thoại {phone} đã có trong hệ thống! Vui lòng kiểm tra lại danh sách.")
            else:
                with st.spinner("Đang lưu dữ liệu..."):
                    row_data = [
                        datetime.now().strftime("%d/%m/%Y %H:%M"), # Ngày nhập
                        name.upper(), # Tên viết hoa
                        yob, hometown, 
                        f"'{phone}", # Thêm dấu ' để Excel không mất số 0 đầu
                        position, status, note, source # Thêm cột Nguồn
                    ]
                    sheet.append_row(row_data)
                    st.toast("✅ Đã lưu thành công!", icon="🎉")
                    time.sleep(1)
                    st.rerun()

# ==========================================
# CHỨC NĂNG 2: DANH SÁCH & TÌM KIẾM
# ==========================================
elif menu == "📋 Danh Sách & Tìm Kiếm":
    st.markdown('<p class="main-header">🔍 Tra Cứu Hồ Sơ</p>', unsafe_allow_html=True)
    
    if df.empty:
        st.info("Chưa có dữ liệu.")
    else:
        # Thanh tìm kiếm
        col_search, col_filter_stt = st.columns([2, 1])
        with col_search:
            search_term = st.text_input("🔎 Tìm kiếm (Tên hoặc SĐT):")
        with col_filter_stt:
            filter_status = st.multiselect("Lọc trạng thái:", df["TrangThai"].unique())

        # Xử lý lọc
        df_display = df.copy()
        if search_term:
            df_display = df_display[df_display.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
        if filter_status:
            df_display = df_display[df_display["TrangThai"].isin(filter_status)]

        st.dataframe(df_display, use_container_width=True, height=500)
        st.caption(f"Hiển thị {len(df_display)} hồ sơ.")

# ==========================================
# CHỨC NĂNG 3: LỊCH PHỎNG VẤN (TÍNH NĂNG MỚI)
# ==========================================
elif menu == "📅 Lịch Phỏng Vấn":
    st.markdown('<p class="main-header">📅 Danh Sách Chờ Phỏng Vấn</p>', unsafe_allow_html=True)
    
    if not df.empty:
        # Lọc ra những người có trạng thái là "Hẹn phỏng vấn" hoặc "Mới nhận"
        df_interview = df[df["TrangThai"].isin(["Hẹn phỏng vấn", "Mới nhận hồ sơ"])]
        
        col1, col2 = st.columns(2)
        col1.metric("Cần phỏng vấn", f"{len(df_interview)} người")
        
        st.write("Dưới đây là danh sách những người cần xử lý:")
        for index, row in df_interview.iterrows():
            with st.expander(f"📌 {row['HoTen']} - {row['ViTri']}"):
                st.write(f"📞 **SĐT:** {row['SDT']}")
                st.write(f"🏠 **Quê quán:** {row['QueQuan']}")
                st.write(f"📝 **Ghi chú:** {row['GhiChu']}")
                st.info(f"Nguồn: {row.get('Nguồn', 'Không rõ')}") # Xử lý nếu chưa có cột Nguồn cũ

# ==========================================
# CHỨC NĂNG 4: BÁO CÁO HIỆU QUẢ
# ==========================================
elif menu == "📊 Báo Cáo Hiệu Quả":
    st.markdown('<p class="main-header">📊 Dashboard Tuyển Dụng</p>', unsafe_allow_html=True)
    
    if not df.empty:
        # KPI Cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tổng hồ sơ", len(df))
        c2.metric("Đạt yêu cầu", len(df[df["TrangThai"].str.contains("Đạt")]))
        c3.metric("Tỉ lệ chuyển đổi", f"{round(len(df[df['TrangThai'].str.contains('Đạt')]) / len(df) * 100, 1)}%")
        c4.metric("Chờ phỏng vấn", len(df[df["TrangThai"] == "Hẹn phỏng vấn"]))
        
        st.markdown("---")
        
        # Biểu đồ
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Tỉ lệ theo Vị trí")
            st.bar_chart(df["ViTri"].value_counts())
            
        with col_chart2:
            # Kiểm tra xem có cột Nguồn không để vẽ biểu đồ
            if "Nguồn" in df.columns: # Giả sử tên cột trong Excel bạn sẽ đặt là 'Nguồn' (nếu chưa có thì lần nhập tới sẽ tự có)
                st.subheader("Hiệu quả kênh tuyển dụng")
                st.bar_chart(df["Nguồn"].value_counts())
            else:
                st.subheader("Phân bổ Trạng thái")
                st.bar_chart(df["TrangThai"].value_counts())
