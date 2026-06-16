# Bài phản ánh cá nhân – Đánh giá truy xuất thông tin

## 1. Thông tin sinh viên

- **Họ và tên:** Nguyễn Văn Huy
- **Mã sinh viên:** 2A202600773
- **Nhóm:** E3
- **Vai trò trong nhóm:** Phụ trách phần Đánh giá truy xuất thông tin

---

## 2. Đóng góp kỹ thuật

Trong bài lab này, em phụ trách hạng mục **Đánh giá truy xuất thông tin**. Đây là một thành phần quan trọng trong quá trình đánh giá hệ thống Agent, đặc biệt đối với các hệ thống có sử dụng kiến trúc RAG. Nhiệm vụ chính của em là đảm bảo rằng hệ thống có khả năng đánh giá chất lượng truy xuất tài liệu trước khi tiến hành đánh giá chất lượng câu trả lời cuối cùng của Agent.

Cụ thể, em đã thực hiện việc cài đặt và kiểm tra logic tính toán chỉ số **Hit Rate** trong file `engine/retrieval_eval.py`. Chỉ số này được sử dụng để xác định liệu trong danh sách các tài liệu được truy xuất bởi hệ thống có xuất hiện ít nhất một tài liệu đúng hay không. Bên cạnh đó, em cũng cài đặt và kiểm tra logic tính toán chỉ số **MRR** trong cùng file. MRR giúp đánh giá vị trí xuất hiện đầu tiên của tài liệu đúng trong danh sách kết quả truy xuất, từ đó phản ánh chất lượng xếp hạng của Retriever.

Ngoài việc triển khai các chỉ số đánh giá, em còn thực hiện đối chiếu giữa trường `expected_retrieval_ids` trong bộ dữ liệu chuẩn và trường `retrieved_ids` do Agent trả về. Quá trình đối chiếu này giúp xác định chính xác liệu hệ thống có truy xuất đúng tài liệu mong đợi hay không. Sau đó, em kiểm tra đầu ra của benchmark nhằm xác nhận rằng các chỉ số Hit Rate và MRR đã được tính toán đúng theo yêu cầu.

File mà em phụ trách chính là:

- `engine/retrieval_eval.py`

Một số file khác được sử dụng để đối chiếu kết quả và phân tích đầu ra gồm:

- `reports/summary.json`
- `reports/benchmark_results.json`
- `analysis/failure_analysis.md`

Tuy nhiên, các file này chỉ được sử dụng để tham khảo và kiểm chứng kết quả, không phải là phần việc chính mà em trực tiếp phụ trách.

---

## 3. Chiều sâu kỹ thuật

Trong quá trình thực hiện, em nhận thấy rằng việc đánh giá chất lượng truy xuất là một bước rất quan trọng đối với hệ thống Agent sử dụng RAG. Chỉ số **Hit Rate** được dùng để kiểm tra xem trong top-k tài liệu mà Retriever trả về có ít nhất một tài liệu đúng hay không. Nếu tài liệu kỳ vọng xuất hiện trong danh sách tài liệu được truy xuất, test case đó được tính là một lượt truy xuất thành công. Chỉ số này giúp đánh giá khả năng Retriever đưa được ngữ cảnh phù hợp vào pipeline xử lý của hệ thống.

Bên cạnh đó, chỉ số **MRR**, hay **Mean Reciprocal Rank**, được sử dụng để đo vị trí xuất hiện đầu tiên của tài liệu đúng trong danh sách truy xuất. Nếu tài liệu đúng xuất hiện ở vị trí đầu tiên, điểm reciprocal rank là 1.0. Nếu tài liệu đúng xuất hiện ở vị trí thứ hai, điểm là 0.5. Nếu tài liệu đúng xuất hiện ở vị trí thứ ba, điểm là khoảng 0.33. Vì vậy, MRR không chỉ cho biết hệ thống có truy xuất được tài liệu đúng hay không, mà còn phản ánh tài liệu đúng có được xếp ở vị trí cao trong danh sách kết quả hay không.

Chất lượng truy xuất có ảnh hưởng trực tiếp đến chất lượng câu trả lời của Agent. Nếu Retriever lấy sai ngữ cảnh, mô hình ngôn ngữ lớn có thể tạo ra câu trả lời sai hoặc thiếu căn cứ, ngay cả khi phần prompt hoặc bộ đánh giá câu trả lời được thiết kế tốt. Ngược lại, nếu Retriever truy xuất đúng tài liệu và xếp tài liệu đó ở vị trí cao, Agent sẽ có nhiều cơ hội tạo ra câu trả lời chính xác, đầy đủ và bám sát nguồn dữ liệu hơn.

---

## 4. Quá trình giải quyết vấn đề

Khó khăn lớn nhất trong phần việc này là phân biệt lỗi do truy xuất thông tin và lỗi do quá trình sinh câu trả lời. Khi một câu trả lời của Agent không đạt yêu cầu, không thể kết luận ngay rằng lỗi đến từ mô hình sinh ngôn ngữ. Trước tiên, cần kiểm tra xem hệ thống có truy xuất đúng ngữ cảnh hay không. Nếu ngữ cảnh đầu vào đã sai hoặc thiếu, câu trả lời cuối cùng rất dễ bị sai lệch.

Để giải quyết vấn đề này, em sử dụng trường `expected_retrieval_ids` trong từng test case làm cơ sở đối chiếu với danh sách `retrieved_ids` do Agent trả về. Cách làm này giúp nhóm xác định rõ hơn nguyên nhân gây lỗi trong từng trường hợp.

Sau khi có kết quả Hit Rate và MRR, nhóm có thể phân tích lỗi một cách rõ ràng hơn. Nếu Hit Rate thấp, lỗi có thể nằm ở quá trình retrieval, chunking hoặc ranking. Nếu Hit Rate cao nhưng điểm chất lượng câu trả lời thấp, nguyên nhân có thể đến từ phần prompting hoặc generation. Trong trường hợp MRR thấp, điều đó cho thấy tài liệu đúng có thể đã xuất hiện trong top-k nhưng bị xếp ở vị trí thấp, khi đó hệ thống có thể cần cải thiện thêm bằng kỹ thuật reranking.

---

## 5. Kết quả đạt được

Kết quả benchmark cuối cùng trong file `reports/summary.json` cho thấy hệ thống đạt:

- **Retrieval Hit Rate:** 1.0
- **Retrieval MRR:** 1.0

Kết quả này cho thấy phiên bản Agent V2 đã truy xuất đúng ngữ cảnh cho toàn bộ bộ test hiện tại. Đồng thời, các tài liệu đúng không chỉ xuất hiện trong danh sách truy xuất mà còn được xếp ở vị trí phù hợp. Điều này chứng minh rằng giai đoạn retrieval của hệ thống đã đáp ứng tốt yêu cầu đánh giá trong rubric đối với bộ dữ liệu benchmark hiện có.

---

## 6. Bài học rút ra

Thông qua nhiệm vụ này, em hiểu rõ hơn rằng việc đánh giá một hệ thống AI Agent không nên chỉ dựa vào câu trả lời cuối cùng. Đối với hệ thống RAG, cần đánh giá từng tầng riêng biệt trong pipeline, đặc biệt là tầng Retrieval, vì đây là bước quyết định chất lượng dữ liệu đầu vào cho mô hình sinh câu trả lời.

Nếu tầng Retrieval hoạt động không tốt, Agent có thể đưa ra câu trả lời thiếu chính xác hoặc không có căn cứ. Ngược lại, khi tầng Retrieval truy xuất được đúng tài liệu và sắp xếp tài liệu ở vị trí cao, chất lượng câu trả lời cuối cùng sẽ được cải thiện đáng kể.

Trong các lần cải tiến tiếp theo, em mong muốn bổ sung thêm các kỹ thuật như **semantic retrieval** và **reranking** để hệ thống có thể xử lý tốt hơn các câu hỏi mở, câu hỏi mơ hồ hoặc các tình huống hội thoại nhiều lượt.
