import pandas as pd
import google.generativeai as genai  
from config import settings
import os
import json
import re

# --- Cấu hình API ---
genai.configure(api_key=settings.GEMINI_API_KEY)  

# --- Hàm đọc danh mục sản phẩm ---
def load_products():
    product_path = os.path.join("data", "products.csv")
    if os.path.exists(product_path):
        try:
            df = pd.read_csv(product_path)
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"Lỗi khi đọc file sản phẩm: {e}")
            return []
    else:
        print("Không tìm thấy file products.csv")
        return []


# --- Hàm tạo đơn hàng ---
def create_order(customer_name, address, phone, product_name, quantity):
    order_path = os.path.join("data", "orders.xlsx")

    new_order = pd.DataFrame([{
        "Tên khách hàng": customer_name,
        "Địa chỉ": address,
        "Số điện thoại": phone,
        "Sản phẩm": product_name,
        "Số lượng": quantity
    }])

    if os.path.exists(order_path):
        existing = pd.read_excel(order_path)
        updated = pd.concat([existing, new_order], ignore_index=True)
        updated.to_excel(order_path, index=False)
    else:
        new_order.to_excel(order_path, index=False)


# --- Hàm sinh phản hồi từ AI ---
def generate_ai_response(user_input, chat_history):
    products = load_products()

    product_text = "\n".join([
        f"- {p['ten_san_pham']} ({p.get('phan_loai', '')}) - {p.get('gia_vnd', '')} VND"
        for p in products
    ]) if products else "Hiện chưa có sản phẩm nào trong danh mục."

    history_text = "\n".join([
        f"{h['role']}: {h['content']}" 
        for h in chat_history
    ])

    # Prompt yêu cầu AI trả về cấu trúc ORDER_INFO
    prompt = f"""
    Bạn là trợ lý CSKH của cửa hàng BHLĐ Triệu Gia. 
    Nhiệm vụ của bạn là tư vấn, hỗ trợ khách hàng và gợi ý sản phẩm phù hợp. 
    Sau khi chốt đơn phải thu thập đủ thông tin của khách hàng bao gồm thông tin sản phẩm size giày size quần áo, thông tin cá nhân và thông tin về đơn hàng.
    Kết thúc quá trình tư vấn mua hàng thì hãy cảm ơn khách hàng, cần hỗ trợ vui lòng liên hệ lại cửa hàng.
    Nếu khách hàng đồng ý mua hàng thì bạn PHẢI trả về đoạn JSON có dạng:

    ORDER_INFO:
    {{
        "name": "Tên khách hàng",
        "address": "Địa chỉ",
        "phone": "Số điện thoại",
        "product": "Tên sản phẩm",
        "quantity": "Số lượng"
    }}

    Nếu khách chưa chốt đơn thì KHÔNG được trả về JSON.

    Danh mục sản phẩm:
    {product_text}

    Lịch sử hội thoại:
    {history_text}

    Tin nhắn khách:
    {user_input}

    Trả lời thân thiện, ngắn gọn.
    """

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")  # 🔧 Sửa cách tạo model
        response = model.generate_content(prompt)          # 🔧 Sửa gọi model
        ai_text = response.text or ""

        # --- Kiểm tra nếu AI trả về ORDER_INFO ---
        match = re.search(r"ORDER_INFO:\s*(\{.*?\})", ai_text, re.DOTALL)
        if match:
            try:
                order_data = json.loads(match.group(1))

                create_order(
                    customer_name=order_data.get("name", "Không rõ"),
                    address=order_data.get("address", "Không rõ"),
                    phone=order_data.get("phone", "Không rõ"),
                    product_name=order_data.get("product", "Không rõ"),
                    quantity=order_data.get("quantity", 1)
                )

                return (
                    "🧾 Đơn hàng đã được tạo thành công!\n"
                    f"• Khách: {order_data.get('name')}\n"
                    f"• SĐT: {order_data.get('phone')}\n"
                    f"• Sản phẩm: {order_data.get('product')}\n"
                    f"• SL: {order_data.get('quantity')}\n\n"
                    "Cửa hàng sẽ liên hệ xác nhận trong ít phút nữa nhé! ❤️"
                )

            except Exception as e:
                return f"❌ Lỗi xử lý ORDER_INFO: {e}"

        # Nếu không chứa ORDER_INFO → trả về phản hồi AI bình thường
        return ai_text

    except Exception as e:
        return f"❌ Lỗi khi gọi AI: {e}"