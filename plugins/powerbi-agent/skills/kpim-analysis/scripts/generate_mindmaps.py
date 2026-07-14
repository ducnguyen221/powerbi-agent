import textwrap, graphviz
OUT="./out"
FONT="DejaVu Sans"
def wrap(t,w=26): return "\\n".join(textwrap.wrap(t,w))
def mind(fname, title, center, branches, ccolor="#111111"):
    g=graphviz.Digraph(engine="dot", format="png")
    g.attr(rankdir="LR", bgcolor="white", fontname=FONT, label=title, labelloc="t", fontsize="26")
    g.attr("node", fontname=FONT, shape="box", style="rounded,filled", fontsize="12", margin="0.12,0.07")
    g.attr("edge", color="#888888", penwidth="1.2")
    g.node("C", center, shape="box", style="rounded,filled", fillcolor=ccolor, fontcolor="white", fontsize="15")
    for i,(cat,color,leaves) in enumerate(branches):
        cid=f"c{i}"
        g.node(cid, cat, fillcolor=color, fontcolor="white", fontsize="13")
        g.edge("C", cid)
        for j,lf in enumerate(leaves):
            lid=f"l{i}_{j}"
            g.node(lid, wrap(lf), fillcolor=color+"22" if len(color)==7 else "#eeeeee", fontcolor="#222222")
            # light fill: use a pale version
            g.node(lid, wrap(lf), fillcolor="#f4f4f8", fontcolor="#222222")
            g.edge(cid, lid)
    g.render(f"{OUT}/{fname}", cleanup=True)
    print("rendered", fname)

# 1. KEY OBJECTIVES
mind("key_objectives","KEY OBJECTIVES MINDMAP","KEY\\nOBJECTIVES",[
 ("Tổng hợp dữ liệu","#2b3fd6",[
   "Tổng hợp dữ liệu SQL Server & Excel chung một nơi để phân tích",
   "Kết nối thông tin giữa các bảng và so sánh thực hiện vs kế hoạch",
   "Gộp dữ liệu từ nhiều bảng"]),
 ("Tính toán thông minh","#3a8a2b",[
   "Tính chính xác các chỉ số theo logic nghiệp vụ",
   "Tính toán thông minh theo thời gian (cùng kỳ năm ngoái, lũy kế năm)",
   "Cho phép so sánh các công thức theo các trường dữ liệu ở các bảng"]),
 ("Trực quan hóa","#e8730c",[
   "Có các trang Dashboard gồm biểu đồ trực quan",
   "Có các bảng phân tích dạng Pivot Table",
   "Có các slicer và cho phép lọc theo dõi theo các điều kiện"]),
 ("Cập nhật & Mở rộng","#7d1e8c",[
   "Cho phép kéo thả tạo ra các nội dung phân tích mới",
   "Có các tính năng truy vết thông tin và dữ liệu",
   "Dễ dàng cập nhật dữ liệu của báo cáo và công thức, biểu đồ",
   "Có tính năng tương tác giữa các biểu đồ"]),
], ccolor="#111111")

# 2. KEY QUESTIONS
mind("key_questions","KEY QUESTIONS MINDMAP","KEY\\nQUESTIONS",[
 ("Hiện trạng chỉ số bán hàng?","#2b3fd6",[
   "Các chỉ số bán hàng như doanh thu, số sản phẩm bán hiện tại là bao nhiêu?",
   "Nếu nhìn theo năm nay hoặc tháng này thì chỉ số này là bao nhiêu?",
   "Nếu nhìn theo từng cửa hàng, quản lý hoặc sản phẩm thì kết quả thế nào?"]),
 ("Kết quả KD có đạt chỉ tiêu?","#3a8a2b",[
   "Cửa hàng nào đạt hoặc không đạt chỉ tiêu?",
   "Quản lý nào đạt hoặc không đạt chỉ tiêu?",
   "Tháng nào đạt hoặc không đạt chỉ tiêu?"]),
 ("Đang tăng trưởng hay suy giảm?","#e8730c",[
   "Tổng doanh thu đang tăng hay giảm so với cùng kỳ năm ngoái?",
   "Cửa hàng/sản phẩm nào tăng trưởng hoặc giảm so với cùng kỳ năm ngoái?",
   "So sánh theo tháng này vs tháng trước và quý này vs quý trước thế nào?"]),
 ("Yếu tố nào gây suy giảm DT?","#7d1e8c",[
   "Xem từng cửa hàng tháng nào không đạt chỉ tiêu?",
   "Xem từng cửa hàng tại tháng nào doanh thu vượt ngưỡng chỉ tiêu theo lũy kế năm?",
   "Tại tháng có doanh thu giảm, cửa hàng nào bị giảm nhiều nhất?",
   "Truy vết cửa hàng suy giảm: tháng nào giảm hoặc sản phẩm nào bán giảm?"]),
], ccolor="#111111")

# 3. KEY ANALYSIS
mind("key_analysis","KEY ANALYSIS MINDMAP","KPIM Mart\\nDữ Liệu Bán Hàng",[
 ("Thời gian","#0f9d8f",["Ngày / Tháng / Quý / Năm"]),
 ("Khách hàng","#0f9d8f",["Phân khúc","Hạng thẻ","Nhóm tuổi","Giới tính"]),
 ("Sản phẩm","#0f9d8f",["Ngành hàng","Nhóm sản phẩm","Phân loại","Nguồn gốc","Hãng, thương hiệu"]),
 ("Khu vực bán hàng","#0f9d8f",["Quận","Cửa hàng","Quản lý"]),
 ("Doanh Thu","#12776e",["Doanh thu lũy kế năm","Tăng trưởng so với tháng trước","Tăng trưởng so với cùng kỳ năm ngoái"]),
 ("Lợi Nhuận Gộp","#12776e",["Giá vốn hàng bán","Biên lợi nhuận gộp"]),
 ("Tổng Khuyến Mãi","#12776e",["Tỷ lệ khuyến mãi","Số sản phẩm chạy khuyến mãi"]),
 ("Số Sản Phẩm Bán","#12776e",["Lợi nhuận trên 1 sản phẩm","Giá bán trung bình 1 sản phẩm"]),
 ("Số Khách Mua Hàng","#12776e",["Tần suất mua hàng TB 1 khách","Bình quân giá trị mua hàng 1 khách"]),
 ("Số Đơn Hàng","#12776e",["Giá trị trung bình 1 đơn hàng","Số sản phẩm mua TB 1 đơn hàng"]),
], ccolor="#0f9d8f")

# 4. KEY REPORT
mind("key_report","KEY REPORT MINDMAP","KPIM Mart\\nBáo cáo Bán Hàng",[
 ("Báo cáo tổng quan","#2b6fd6",[
   "Tổng quan doanh thu / lợi nhuận gộp / số sản phẩm / đơn hàng bán",
   "So sánh chỉ số lựa chọn theo quận / cửa hàng",
   "So sánh chỉ số lựa chọn theo tháng / năm",
   "So sánh chỉ số lựa chọn theo ngành hàng / sản phẩm"]),
 ("BC phân tích doanh thu","#2b6fd6",[
   "Doanh số / số kế hoạch / tăng trưởng so với cùng kỳ năm ngoái",
   "Xu hướng doanh thu 12 tháng năm nay vs năm ngoái",
   "Doanh thu theo từng quận/cửa hàng + tỷ lệ tăng trưởng so cùng kỳ",
   "Doanh thu lũy kế năm của cửa hàng/quản lý vs chỉ tiêu lũy kế năm"]),
 ("BC phân tích tái mua hàng","#2b6fd6",[
   "Số khách hàng mới / cũ / duy trì mua hàng so với tháng trước",
   "Tỷ trọng khách hàng quay lại mua theo quý / nửa năm / 1 năm"]),
 ("BC kết quả theo khu vực","#2b6fd6",[
   "Số cửa hàng đạt kế hoạch / tăng trưởng hoặc không đạt so năm ngoái",
   "So sánh % tiến độ doanh thu đạt chỉ tiêu theo từng cửa hàng",
   "So sánh % tăng trưởng so cùng kỳ năm ngoái từng cửa hàng"]),
 ("BC phân khúc khách hàng","#2b6fd6",[
   "Trung bình giá trị đơn hàng trên 1 khách hàng",
   "Số khách theo phân loại: quan trọng / thường xuyên / ít mua",
   "Doanh thu theo nhóm thông tin KH: độ tuổi / nghề nghiệp / giới tính"]),
 ("BC giám sát biên LN gộp","#2b6fd6",[
   "Tổng quan doanh số / giá vốn / lợi nhuận gộp / biên lợi nhuận gộp",
   "So sánh lợi nhuận gộp theo từng cửa hàng",
   "So sánh giá bán / giá mua / lợi nhuận và biên lợi nhuận từng sản phẩm"]),
], ccolor="#123f8c")
print("DONE mindmaps")
