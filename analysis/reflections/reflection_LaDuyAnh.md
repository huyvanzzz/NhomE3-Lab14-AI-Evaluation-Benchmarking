# Individual Reflection - La Duy Anh

## Student Information
- Name: La Duy Anh
- Role: Regression Testing Lead (rubric item #4, 10 điểm — `analysis/report_role_plan.md`)

## Engineering Contribution
- Phụ trách `main.py`: chạy benchmark cho cả hai phiên bản Agent
  (`Agent_V1_Base` và `Agent_V2_Optimized`) trên cùng một golden dataset, rồi so
  sánh kết quả qua hai khối logic chính:
  - `build_regression(v1, v2)`: tính delta giữa V2 và V1 cho 5 chỉ số —
    `avg_score`, `hit_rate`, `mrr`, `cost_usd`, `runtime_sec` — và ghi vào
    `reports/summary.json["regression"]`.
  - `build_release_gate(v1, v2)`: Auto-Gate quyết định `APPROVE` hay
    `BLOCK_RELEASE`, lưu vào `reports/summary.json["release_gate"]`, dựa trên 5
    điều kiện đồng thời (logic AND, không phải chỉ nhìn 1 chỉ số):
    1. `avg_score` của V2 không thấp hơn V1 (không hồi quy chất lượng).
    2. `hit_rate` của V2 ≥ 0.80.
    3. `mrr` của V2 ≥ 0.60.
    4. `agreement_rate` (Multi-Judge) của V2 ≥ 0.70.
    5. Chi phí/case của V2 không tăng quá 30% so với V1 (`safe_delta_ratio`).
- Thêm comment giải thích ý nghĩa từng ngưỡng trong `RELEASE_THRESHOLDS` và lý do
  dùng logic AND cho 5 check trong `build_release_gate`, để người đọc sau không cần
  suy luận lại từ đầu.
- Đã verify end-to-end: `python data/synthetic_gen.py` → `python main.py` →
  in ra `Regression summary` + `Release gate decision: APPROVE` → kiểm tra trực
  tiếp `reports/summary.json` có đủ cả 2 khối `regression` và `release_gate` →
  `python check_lab.py` → `[READY]`.
- Evidence từ commit: thay đổi giới hạn trong `main.py` (chỉ phần comment giải
  thích, không đổi logic gốc của `build_regression`/`build_release_gate` vì logic
  này đã hoạt động đúng), `analysis/report_role_plan.md` (điền tên dòng Role 4), và
  file reflection này — không sửa `engine/llm_judge.py` hay
  `engine/retrieval_eval.py` theo đúng quy ước chống conflict của nhóm.

## Technical Depth
- **Vì sao so sánh V1 vs V2:** Regression Testing trả lời câu hỏi "bản cập nhật
  Agent có thực sự tốt hơn không, hay chỉ tốt hơn ở 1 chỉ số và tệ hơn ở chỉ số
  khác?". Chạy cả 2 phiên bản trên **cùng** golden dataset là điều kiện bắt buộc để
  so sánh công bằng — nếu dataset khác nhau, delta sẽ không phản ánh đúng sự cải
  tiến của Agent.
- **Delta metrics:** mỗi delta là `V2 - V1` (hoặc tỉ lệ phần trăm với chi phí, dùng
  `safe_delta_ratio` để tránh chia cho 0 khi baseline cost = 0). Delta dương ở
  `avg_score`/`hit_rate`/`mrr` là tín hiệu tốt; delta âm ở `cost_usd`/`runtime_sec`
  cũng là tín hiệu tốt (rẻ hơn, nhanh hơn). Kết quả thực tế đo được:
  `delta_avg_score=+2.212`, `delta_hit_rate=+0.0`, `delta_mrr=+0.552`,
  `delta_cost_usd=-0.00445`, `delta_runtime_sec=-0.172` — V2 vừa tốt hơn vừa rẻ
  hơn/nhanh hơn V1.
- **Lý do Release Gate APPROVE:** cả 5 check đều `true` — `avg_score` không hồi
  quy, `hit_rate` (1.0) và `mrr` (1.0) đều vượt xa ngưỡng 0.8/0.6, `agreement_rate`
  (1.0) vượt ngưỡng 0.7, và chi phí giảm (~-33.1%) nên không vi phạm ngưỡng tăng
  chi phí tối đa 30%. Vì không có điều kiện nào vi phạm, Auto-Gate trả về
  `APPROVE` thay vì `BLOCK_RELEASE`.
- **Trade-off Chi phí vs Chất lượng:** một Release Gate chỉ dựa vào `avg_score` là
  không đủ trong thực tế sản phẩm — một bản cập nhật có thể tăng điểm chất lượng
  nhưng tăng chi phí/latency vượt mức chấp nhận được. Đó là lý do `RELEASE_THRESHOLDS`
  có cả ngưỡng `max_cost_increase`, không chỉ ngưỡng chất lượng (`hit_rate`, `mrr`,
  `agreement_rate`).

## Problem Solving
- Hardest issue encountered: hiểu đúng "hợp đồng dữ liệu" (data contract) mà
  `build_regression`/`build_release_gate` phụ thuộc vào — cả hai hàm đọc trực tiếp
  từ `v1["metrics"]`/`v2["metrics"]`/`v1["cost"]`/`v2["cost"]`, vốn được tạo ra bởi
  `build_summary()` (dùng kết quả từ `engine/llm_judge.py` và
  `engine/retrieval_eval.py`). Nếu sửa nhầm format ở các module đó mà không phối
  hợp, `main.py` sẽ lỗi KeyError ngay khi chạy.
- Debugging approach: chạy lại toàn bộ pipeline (`synthetic_gen.py` → `main.py` →
  `check_lab.py`) sau mỗi lần chỉnh sửa, in trực tiếp `reports/summary.json` bằng
  Python để xác nhận đúng cấu trúc `regression`/`release_gate` trước khi coi là
  hoàn thành, thay vì chỉ tin vào log console.
- Final resolution: giữ nguyên toàn bộ logic tính toán đã đúng của
  `build_regression`/`build_release_gate`, chỉ bổ sung comment giải thích ý nghĩa
  ngưỡng và lý do dùng logic AND, tránh rủi ro sửa nhầm logic đang hoạt động đúng.

## Lessons Learned
- What I would improve next: thêm test giả lập trường hợp `BLOCK_RELEASE` (ví dụ
  cố tình hạ `hit_rate` của V2 dưới 0.8) để chứng minh Auto-Gate phản ứng đúng ở cả
  hai chiều, không chỉ test trường hợp APPROVE; đồng thời log rõ "check nào fail"
  ra console (không chỉ JSON) để dễ debug khi release bị chặn trong CI thực tế.
