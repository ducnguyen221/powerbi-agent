import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
# pick a font supporting Vietnamese
for f in ["DejaVu Sans"]:
    plt.rcParams["font.family"]=f
rows=[
["1","Mã giao dịch","Text","Mã định danh giao dịch mua bán đơn hàng"],
["2","Ngày đặt hàng","Date","Ngày phát sinh đơn hàng, đặt bởi khách hàng"],
["3","Tên cửa hàng","List","Cửa hàng trên hệ thống phát sinh đơn hàng"],
["4","Sản phẩm","List","Sản phẩm được đặt hàng"],
["5","Khuyến mãi","List","Chương trình giảm giá áp dụng"],
["6","Số lượng","Whole Number","Số lượng sản phẩm mua (Additive)"],
["7","Số điện thoại","Text","Số điện thoại định danh khách hàng"],
["8","Tên khách hàng","Text","Tên của khách hàng trên hệ thống"],
["9","Giá bán","Decimal","Giá bán cho 1 đơn vị sản phẩm (Non-additive)"],
["10","Giá mua","Decimal","Giá vốn mua nhập sản phẩm về (Non-additive)"],
["11","Tổng giá tiền","Decimal","Số lượng * Giá bán"],
["12","Tổng giảm giá","Decimal","Số lượng * Tỷ lệ giảm giá"],
["13","Tổng doanh thu","Decimal","Tổng giá tiền - Tổng giảm giá"],
["14","Giá vốn hàng bán","Decimal","Số lượng * Giá mua"],
["15","Lợi nhuận gộp","Decimal","Tổng doanh thu - Giá vốn hàng bán"],
]
cols=["STT","Tên cột","Loại dữ liệu","Định nghĩa"]
fig,ax=plt.subplots(figsize=(12,6.2)); ax.axis("off")
ax.set_title("KEY DATA DICTIONARY — KPIM Mart (Bảng Đơn Hàng Bán)", fontsize=15, weight="bold", color="#1f3a5f", pad=14)
t=ax.table(cellText=rows, colLabels=cols, cellLoc="left", loc="center",
           colWidths=[0.06,0.22,0.16,0.56])
t.auto_set_font_size(False); t.set_fontsize(10); t.scale(1,1.5)
for (r,c),cell in t.get_celld().items():
    cell.set_edgecolor("#c9d3e6")
    if r==0:
        cell.set_facecolor("#3f5b8c"); cell.set_text_props(color="white", weight="bold")
    else:
        cell.set_facecolor("#eef2f9" if r%2 else "#dde5f2")
plt.savefig("./out/key_data_dictionary.png", dpi=140, bbox_inches="tight")
print("dd done")
