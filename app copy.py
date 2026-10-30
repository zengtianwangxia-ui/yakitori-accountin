import streamlit as st
from datetime import datetime

st.title("焼き鳥販売システム")

# 販売価格（仮の金額）
prices = {
    1: 120,
    2: 220,
    4: 400
}

# 商品一覧
products = [
    "もも・タレ",
    "もも・塩",
    "ネギま・タレ",
    "ネギま・塩"
]

# 販売データの初期化
if "product_counts" not in st.session_state:
    st.session_state.product_counts = {
        product: 0 for product in products
    }

if "set_counts" not in st.session_state:
    st.session_state.set_counts = {
        1: 0,
        2: 0,
        4: 0
    }

if "sales" not in st.session_state:
    st.session_state.sales = 0

if "sales_history" not in st.session_state:
    st.session_state.sales_history = []

# 現在選択している商品の本数
if "quantities" not in st.session_state:
    st.session_state.quantities = {
        product: 0 for product in products
    }


# 商品の本数を変更する関数
def change_quantity(product, amount):
    current = st.session_state.quantities[product]
    st.session_state.quantities[product] = max(
        0, current + amount
    )

def cancel_sale(index):
    # 取り消す販売記録を取得する
    record = st.session_state.sales_history[index]

    # すでに取り消されていたら何もしない
    if record.get("cancelled", False):
        return

    # 商品別の販売本数を元に戻す
    for product, count in record["quantities"].items():
        st.session_state.product_counts[product] -= count

    # 販売方法別のセット数を元に戻す
    pack_size = record["pack_size"]
    st.session_state.set_counts[pack_size] -= 1

    # 売上金額を元に戻す
    st.session_state.sales -= record["price"]

    # 履歴は削除せず、取り消し済みにする
    record["cancelled"] = True


# 販売方法の選択
st.subheader("① 販売方法を選択")

pack_size = st.radio(
    "販売方法",
    options=[1, 2, 4],
    format_func=lambda n: f"{n}本（{prices[n]}円）",
    horizontal=True
)

st.divider()

# 商品の選択
st.subheader("② 商品を選択")

st.write("「＋」「－」を押して、それぞれの本数を調整してね。")

# 商品を2列ずつ表示
for row_start in range(0, len(products), 2):
    col1, col2 = st.columns(2)

    row_products = products[row_start:row_start + 2]

    for col, product in zip([col1, col2], row_products):
        with col:
            with st.container(border=True):
                st.markdown(f"### {product}")

                minus_col, count_col, plus_col = st.columns([1, 1, 1])

                with minus_col:
                    st.button(
                        "－",
                        key=f"minus_{product}",
                        on_click=change_quantity,
                        args=(product, -1),
                        disabled=(
                            st.session_state.quantities[product] == 0
                        ),
                        use_container_width=True
                    )

                with count_col:
                    st.markdown(
                        f"<div style='text-align:center;"
                        f"font-size:24px;font-weight:bold;"
                        f"padding-top:4px'>"
                        f"{st.session_state.quantities[product]}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                with plus_col:
                    st.button(
                        "＋",
                        key=f"plus_{product}",
                        on_click=change_quantity,
                        args=(product, 1),
                        use_container_width=True
                    )

# 現在の選択本数
total = sum(st.session_state.quantities.values())

st.divider()

st.subheader("③ 販売内容を確認")

st.metric(
    "選択中の本数",
    f"{total} / {pack_size}本"
)

if total < pack_size:
    st.info(f"あと{pack_size - total}本選んでね。")
elif total > pack_size:
    st.warning(f"{total - pack_size}本多いよ。商品を減らしてね。")
else:
    st.success("本数が一致しています！")

# 販売確定
if st.button(
    "販売を確定",
    type="primary",
    use_container_width=True,
    disabled=(total != pack_size)
):
    # 商品別の販売本数を加算
    for product, count in st.session_state.quantities.items():
        st.session_state.product_counts[product] += count

    # セット数と売上金額を加算
    st.session_state.set_counts[pack_size] += 1
    st.session_state.sales += prices[pack_size]

    # 今回の販売内容を記録
    sale_record = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "pack_size": pack_size,
        "price": prices[pack_size],
        "quantities": {
            product: count
            for product, count in st.session_state.quantities.items()
            if count > 0
        },
        "cancelled": False
    }

    # 販売履歴に追加
    st.session_state.sales_history.append(sale_record)

    # 次のお客さんに備えて入力をリセット
    st.session_state.quantities = {
        product: 0 for product in products
    }

    st.success(
        f"{pack_size}本セットを"
        f"{prices[pack_size]}円で販売しました！"
    )

st.divider()

st.subheader("販売履歴")

if len(st.session_state.sales_history) == 0:
    st.write("まだ販売履歴はありません。")
else:
    for index, record in reversed(
        list(enumerate(st.session_state.sales_history))
    ):
        items = [
            f"{product} {count}本"
            for product, count in record["quantities"].items()
        ]
        details = "、".join(items)

        with st.container(border=True):
            st.write(f"**{record['time']}**")
            st.write(
                f"{record['pack_size']}本セット：{details}"
            )
            st.write(f"販売金額：{record['price']:,}円")

            if record.get("cancelled", False):
                st.warning("取り消し済み")
            else:
                # 取り消し確認中かどうかを記録する
                confirm_key = f"confirm_cancel_{index}"

                if st.session_state.get(confirm_key, False):
                    st.warning(
                        f"本当にこの販売（{record['price']:,}円）"
                        "を取り消しますか？"
                    )

                    confirm_col, cancel_col = st.columns(2)

                    with confirm_col:
                        st.button(
                            "取り消しを確定",
                            key=f"confirm_{index}",
                            type="primary",
                            use_container_width=True,
                            on_click=cancel_sale,
                            args=(index,)
                        )

                    with cancel_col:
                        st.button(
                            "やめる",
                            key=f"abort_{index}",
                            use_container_width=True,
                            on_click=lambda k=confirm_key:
                                st.session_state.update({k: False})
                        )
                else:
                    st.button(
                        "この販売を取り消す",
                        key=f"cancel_{index}",
                        use_container_width=True,
                        on_click=lambda k=confirm_key:
                            st.session_state.update({k: True})
                    )
st.divider()

# 売上集計
st.subheader("現在の売上")

st.metric(
    "売上金額",
    f"{st.session_state.sales:,}円"
)

st.subheader("商品別の販売本数")

for product, count in st.session_state.product_counts.items():
    st.write(f"{product}：{count}本")

st.subheader("販売方法別のセット数")

for size, count in st.session_state.set_counts.items():
    st.write(f"{size}本セット：{count}セット")

total_bottles = sum(st.session_state.product_counts.values())
total_sets = sum(st.session_state.set_counts.values())

st.write(f"販売本数の合計：{total_bottles}本")
st.write(f"販売セット数の合計：{total_sets}セット")

