import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Tuyển Dụng KCN Pro", layout="wide", page_icon="🏭")

# --- KẾT NỐI GOOGLE SHEETS ---
# Hàm này giúp kết nối mà không bị chậm (cache)
@st.cache_resource
def connect_to_gsheet():
    # Lấy thông tin bảo mật từ Streamlit Secrets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    # Mở file Google Sheet theo tên
    sheet = client.open("TuyenDungKCN_Data").sheet1 
    return sheet

try:
    sheet = connect_to_gsheet()
except Exception as e:
    st.error("⚠️ Chưa kết nối được Google Sheet. Hãy kiểm tra lại phần cài đặt Secrets!")
    st.stop()

# --- GIAO DIỆN CHÍNH ---
st.title("🏭 Hệ Thống Tuyển Dụng Khu Công Nghiệp")
st.markdown("---")

# --- THANH MENU BÊN TRÁI ---
with st.sidebar:
    st.header("Điều Khiển")
    menu = st.radio("Chọn tác vụ:", ["📝 Thêm Ứng Viên", "📋 Danh Sách & Tìm Kiếm", "📊 Báo Cáo Tổng Quan"])
    st.info("💡 Mẹo: Dữ liệu được lưu trực tiếp vào Google Drive của bạn.")

# --- CHỨC NĂNG 1: THÊM ỨNG VIÊN ---
if menu == "📝 Thêm Ứng Viên":
    st.subheader("Nhập thông tin ứng viên mới")
    with st.form("form_add", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Họ và tên (*)", placeholder="Ví dụ: Nguyễn Văn A")
            yob = st.number_input("Năm sinh", 1960, 2010, 2000)
            hometown = st.text_input("Quê quán", placeholder="Ví dụ: Thanh Sơn, Phú Thọ")
            phone = st.text_input("Số điện thoại (*)")
        with col2:
            position = st.selectbox("Vị trí ứng tuyển", ["Công nhân may", "Lắp ráp điện tử", "Kỹ thuật", "QC/KCS", "Kho", "Bảo vệ", "Tạp vụ"])
            status = st.selectbox("Trạng thái hiện tại", ["Mới nhận hồ sơ", "Đã phỏng vấn", "Đạt - Chờ đi làm", "Đã đi làm", "Không đạt", "Lưu hồ sơ"])
            note = st.text_area("Ghi chú phỏng vấn", placeholder="Ví dụ: Có kinh nghiệm may 2 năm, đi làm ngay được...")
        
        btn_submit = st.form_submit_button("Lưu Vào Google Sheet 🚀")
        
        if btn_submit:
            if not name or not phone:
                st.warning("Vui lòng điền tên và số điện thoại!")
            else:
                with st.spinner("Đang gửi dữ liệu lên mây..."):
                    row_data = [
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                        name, yob, hometown, phone, position, status, note
                    ]
                    sheet.append_row(row_data)
                    st.success(f"✅ Đã thêm ứng viên {name} thành công!")

# --- CHỨC NĂNG 2: DANH SÁCH & TÌM KIẾM ---
elif menu == "📋 Danh Sách & Tìm Kiếm":
    st.subheader("Dữ liệu ứng viên")
    
    # Tải dữ liệu mới nhất
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    if df.empty:
        st.warning("Chưa có dữ liệu nào. Hãy nhập thêm ứng viên!")
    else:
        # Bộ lọc tìm kiếm
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            search_term = st.text_input("🔍 Tìm kiếm (Tên, SĐT, Quê quán):")
        with col_filter:
            filter_pos = st.multiselect("Lọc theo vị trí:", df["ViTri"].unique())
            
        # Xử lý lọc
        if search_term:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
        if filter_pos:
            df = df[df["ViTri"].isin(filter_pos)]
            
        st.dataframe(df, use_container_width=True)
        st.caption(f"Tìm thấy {len(df)} hồ sơ.")

# --- CHỨC NĂNG 3: BÁO CÁO ---
elif menu == "📊 Báo Cáo Tổng Quan":
    st.subheader("Thống kê tình hình tuyển dụng")
    
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tổng hồ sơ", len(df))
        col2.metric("Đã đi làm", len(df[df["TrangThai"] == "Đã đi làm"]))
        col3.metric("Chờ nhận việc", len(df[df["TrangThai"] == "Đạt - Chờ đi làm"]))
        col4.metric("Tỉ lệ đạt", f"{round(len(df[df['TrangThai'].str.contains('Đạt|Đã đi làm')]) / len(df) * 100)}%")
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Phân bổ theo Vị trí**")
            st.bar_chart(df["ViTri"].value_counts())
        with c2:
            st.write("**Phân bổ theo Trạng thái**")
            st.bar_chart(df["TrangThai"].value_counts())
    else:
        st.info("Chưa có đủ dữ liệu để vẽ biểu đồ.")