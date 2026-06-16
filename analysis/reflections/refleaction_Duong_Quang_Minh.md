# Individual Reflection - Dương Quang Minh

## Student Information
- Name: Dương Quang Minh
- Student ID: 2A202600686
- Role: Failure Analysis

## Scope of Work
Trong dự án này, em phụ trách phần `Failure Analysis`, tập trung vào việc đọc toàn bộ repo, phân tích kết quả benchmark, tìm cụm lỗi chính, viết báo cáo nguyên nhân gốc và đề xuất hướng cải thiện có thể hành động được.

## Engineering Contribution
- Đọc toàn bộ các file chính trong repo để hiểu luồng dữ liệu từ `data/synthetic_gen.py`, `agent/main_agent.py`, `engine/*`, `main.py`, `reports/*`, đến `analysis/*`.
- Tạo script tái lập báo cáo lỗi tại `analysis/generate_failure_analysis.py` để báo cáo không còn là tài liệu viết tay mà được sinh trực tiếp từ `reports/summary.json` và `reports/benchmark_results.json`.
- Viết lại `analysis/failure_analysis.md` theo hướng có bằng chứng:
  - so sánh `Agent_V1_Base` với `Agent_V2_Optimized`,
  - cluster các lỗi thật của baseline,
  - phân tích `5 Whys` cho các lỗi quan trọng nhất,
  - ghi nhận residual risks của candidate dù candidate đã pass 100%.
- Chạy benchmark và kiểm tra đầu ra bằng `python main.py` và `python check_lab.py` để xác nhận báo cáo khớp với kết quả thực tế.
- Commit và push riêng phần việc của em lên nhánh GitHub cá nhân để không làm lẫn các thay đổi chưa hoàn tất của các thành viên khác.

## Key Results
- Xác định được baseline `Agent_V1_Base` chỉ pass `6/60`, trong khi `Agent_V2_Optimized` pass `60/60`.
- Chỉ ra 3 cụm lỗi lớn ở baseline:
  - `low_judge_score`: 48 cases
  - `retrieval_miss`: 4 cases
  - `unsafe_compliance`: 2 cases
- Phân tích nguyên nhân gốc cho từng nhóm lỗi:
  - baseline trả lời theo top-1 chunk dù document đúng đã nằm trong top-k,
  - fallback retrieval trả về context rác cho câu hỏi out-of-context,
  - logic refusal với adversarial prompt chưa đủ mạnh.
- Ghi nhận rủi ro còn lại ở candidate:
  - một số case multi-turn vẫn kéo theo distractor document,
  - câu hỏi tổng hợp nhiều nguồn chưa retrieve đủ toàn bộ expected docs,
  - còn các case có dấu hiệu `position_bias_detected`.

## Technical Depth
- Em hiểu `benchmarking` là quá trình đo lường hệ thống bằng một tập test và metric chuẩn để có thể so sánh định lượng giữa các phiên bản.
- Em dùng kết quả `Hit Rate` và `MRR` để liên hệ chất lượng retrieval với chất lượng answer, đặc biệt ở các case baseline lấy đúng tài liệu nhưng xếp sai thứ hạng.
- Em dùng `agreement_rate`, `cohens_kappa` và `position_bias_detected` để đánh giá độ ổn định của multi-judge, thay vì chỉ nhìn điểm cuối cùng.
- Em tách rõ `fixed failures` của baseline với `residual risks` của candidate để báo cáo sâu hơn, vì candidate hiện tại không còn failure blocking nào.

## Problem Solving
- Khó khăn lớn nhất là candidate đang pass toàn bộ test, nên nếu chỉ nhìn bản mới thì báo cáo failure analysis sẽ rất nông.
- Cách giải quyết của em là quay lại đọc `reports/benchmark_results.json`, dùng failures của `Agent_V1_Base` làm dữ liệu chính cho root-cause analysis, rồi dùng `Agent_V2_Optimized` để phân tích residual risk.
- Một vấn đề khác là worktree đang có nhiều thay đổi của các thành viên khác. Em xử lý bằng cách chỉ stage đúng các file thuộc phạm vi của mình để commit không làm ảnh hưởng phần việc của người khác.
- Trong lúc sinh báo cáo, em cũng phát hiện thứ tự chạy script có thể khiến `main.py` ghi đè file phân tích. Em đã chạy lại theo đúng thứ tự để đảm bảo báo cáo cuối cùng là bản sâu hơn và nhất quán với benchmark.

## Lessons Learned
- Failure analysis tốt không chỉ là liệt kê case fail, mà phải chỉ ra được vì sao hệ thống sai ở từng lớp: retrieval, generation, judge hay release gate.
- Một báo cáo tốt nên tái lập được từ dữ liệu benchmark thay vì phụ thuộc vào viết tay.
- Nếu tiếp tục phát triển, em muốn:
  - thêm semantic reranking để giảm phụ thuộc vào lexical ranking,
  - thêm confidence gate cho câu hỏi out-of-context,
  - siết chặt tiêu chí retrieval coverage cho các câu hỏi tổng hợp nhiều tài liệu.
