# Báo cáo cá nhân - Trần Quốc Khánh (MSV: 2A202600679)
**Nhóm:** E3 (Lab Day 14 - AI Evaluation Factory)
**Thành viên:** Trần Quốc Khánh (MSV: 2A202600679)

Dựa trên tiêu chí đánh giá cá nhân (Grading Rubric), dưới đây là chi tiết các đóng góp và phân tích kỹ thuật của tôi trong dự án **AI Evaluation Factory**.

---

## 1. Engineering Contribution (Đóng góp kỹ thuật)
- **Vai trò chính:** Trực tiếp phát triển, tích hợp và tối ưu module **Multi-Judge Consensus Engine**.
- **Giải trình kỹ thuật:**
  - **Kiến trúc Multi-Judge:** Thiết kế pipeline cho phép chạy song song ít nhất 2 model Judge (ví dụ: kết hợp một model lớn như GPT-4o và một model tốc độ cao/chi phí thấp như Gemini 1.5 Flash).
  - **Calibration & Consensus Logic:** Viết thuật toán đánh giá độ đồng thuận (Agreement Rate) giữa các giám khảo. 
  - **Tự động xử lý xung đột (Conflict Resolution):** Triển khai cơ chế phân xử tự động. Nếu điểm số của 2 Judge lệch nhau quá ngưỡng cho phép (ví dụ: lệch > 1 điểm trên thang 5), hệ thống sẽ tự động kích hoạt một Judge thứ 3 (Tie-breaker) hoặc ưu tiên trọng số (weight) của model mạnh hơn.
  - **Tối ưu Async:** Phối hợp thiết kế lại luồng gọi API sang dạng bất đồng bộ (`asyncio`) cho Multi-Judge, giúp chạy đồng loạt nhiều test case để giảm thời gian thực thi tổng thể.
- **Bằng chứng Git Commit:** Các thay đổi chính được đóng góp vào module `engine/llm_judge.py` và luồng chạy chính trong `engine/runner.py`.
