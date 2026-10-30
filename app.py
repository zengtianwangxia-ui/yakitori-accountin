import os
import streamlit as st
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
from datetime import datetime

# .envファイルから接続情報を読み込む
load_dotenv()

try:
    DATABASE_URL = st.secrets["DATABASE_URL"]
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL")

st.markdown(
    "<h3 style='margin: 0 0 8px 0; white-space: nowrap;'>"
    "焼き鳥販売システム</h3>",
    unsafe_allow_html=True
)

# 販売価格（仮の金額）
prices = {
    1: 100,
    2: 200,
    4: 350
}

# 商品一覧
products = [
    "もも・タレ",
    "もも・塩",
    "ネギま・タレ",
    "ネギま・塩"
]


# データベースから販売履歴を読み込む
def load_sales_history():
    connection = psycopg2.connect(DATABASE_URL)

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT id, sold_at, pack_size, price,
                   quantities, cancelled
            FROM public.sales_history
            ORDER BY id ASC
        """)

        rows = cursor.fetchall()

        history = []

        for row in rows:
            sale_id, sold_at, pack_size, price, quantities, cancelled = row

            history.append({
                "id": sale_id,
                "time": sold_at.astimezone().strftime("%H:%M:%S"),
                "pack_size": pack_size,
                "price": price,
                "quantities": quantities,
                "cancelled": cancelled
            })

        return history

    finally:
        connection.close()


# データベースに販売記録を保存する
def save_sale(pack_size, price, quantities):
    connection = psycopg2.connect(DATABASE_URL)

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO public.sales_history
                (pack_size, price, quantities)
            VALUES (%s, %s, %s)
            RETURNING id, sold_at
        """, (
            pack_size,
            price,
            Json(quantities)
        ))

        sale_id, sold_at = cursor.fetchone()

        connection.commit()

        return {
            "id": sale_id,
            "time": sold_at.astimezone().strftime("%H:%M:%S"),
            "pack_size": pack_size,
            "price": price,
            "quantities": quantities,
            "cancelled": False
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# データベース上の販売記録を取り消す
def cancel_sale(index):
    record = st.session_state.sales_history[index]

    if record.get("cancelled", False):
        return

    connection = psycopg2.connect(DATABASE_URL)

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE public.sales_history
            SET cancelled = TRUE
            WHERE id = %s AND cancelled = FALSE
            RETURNING id
        """, (record["id"],))

        updated_record = cursor.fetchone()

        if updated_record is None:
            connection.rollback()
            return

        connection.commit()
        record["cancelled"] = True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# 初回だけデータベースから販売履歴を読み込む
if "sales_history" not in st.session_state:
    try:
        st.session_state.sales_history = load_sales_history()

    except Exception:
        st.error(
            "販売履歴を読み込めませんでした。"
            "接続設定やデータベースを確認してください。"
        )
        st.stop()


# 現在選択している商品の本数
if "quantities" not in st.session_state:
    st.session_state.quantities = {
        product: 0 for product in products
    }

def cancel_all_sales():
    connection = psycopg2.connect(DATABASE_URL)
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE public.sales_history
            SET cancelled = TRUE
            WHERE cancelled = FALSE
            RETURNING id
        """)
        cancelled_ids = [row[0] for row in cursor.fetchall()]
        connection.commit()
        return cancelled_ids
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

# 商品の本数を変更する関数
def change_quantity(product, amount):
    current = st.session_state.quantities[product]

    st.session_state.quantities[product] = max(
        0, current + amount
    )


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

for row_start in range(0, len(products), 2):
    col1, col2 = st.columns(2)

    row_products = products[row_start:row_start + 2]

    for col, product in zip([col1, col2], row_products):
        with col:
            with st.container(border=True):
                st.markdown(
                    f"<div style='font-size:16px; font-weight:bold; "
                    f"white-space:nowrap; margin-bottom:4px;'>{product}</div>",
                    unsafe_allow_html=True
                )

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
    st.warning(
        f"{total - pack_size}本多いよ。商品を減らしてね。"
    )

else:
    st.success("本数が一致しています！")


# 販売確定
if st.button(
    "販売を確定",
    type="primary",
    use_container_width=True,
    disabled=(total != pack_size)
):
    quantities = {
        product: count
        for product, count in st.session_state.quantities.items()
        if count > 0
    }

    try:
        # 先にデータベースへ保存する
        sale_record = save_sale(
            pack_size,
            prices[pack_size],
            quantities
        )

        # 保存に成功したら画面の履歴にも追加する
        st.session_state.sales_history.append(sale_record)

        # 次のお客さんに備えて入力をリセット
        st.session_state.quantities = {
            product: 0 for product in products
        }

        st.success(
            f"{pack_size}本セットを"
            f"{prices[pack_size]}円で販売しました！"
        )

    except Exception:
        st.error(
            "販売記録を保存できませんでした。"
            "通信状態やデータベースを確認してください。"
        )


st.divider()

# 販売履歴
st.subheader("販売履歴")

# 一括取り消しの確認状態
if "confirm_cancel_all" not in st.session_state:
    st.session_state.confirm_cancel_all = False

# 取り消されていない販売があるか確認
has_active_sales = any(
    not record.get("cancelled", False)
    for record in st.session_state.sales_history
)

if st.button(
    "全販売記録を取り消す",
    disabled=not has_active_sales,
    use_container_width=True
):
    st.session_state.confirm_cancel_all = True

# 確認画面
if st.session_state.confirm_cancel_all:
    st.warning(
        "本当にすべての販売記録を取り消しますか？"
        "この操作は元に戻せません。"
    )

    confirm_col, cancel_col = st.columns(2)

    with confirm_col:
        if st.button(
            "一括取り消しを確定",
            type="primary",
            use_container_width=True
        ):
            try:
                cancel_all_sales()

                # 画面上の履歴も更新
                for record in st.session_state.sales_history:
                    record["cancelled"] = True

                st.session_state.confirm_cancel_all = False
                st.success("すべての販売記録を取り消しました！")
                st.rerun()

            except Exception:
                st.error("一括取り消しに失敗しました。")

    with cancel_col:
        if st.button(
            "やめる",
            use_container_width=True
        ):
            st.session_state.confirm_cancel_all = False
            st.rerun()

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
                confirm_key = f"confirm_cancel_{record['id']}"

                if st.session_state.get(confirm_key, False):
                    st.warning(
                        f"本当にこの販売（{record['price']:,}円）"
                        "を取り消しますか？"
                    )

                    confirm_col, cancel_col = st.columns(2)

                    with confirm_col:
                        st.button(
                            "取り消しを確定",
                            key=f"confirm_{record['id']}",
                            type="primary",
                            use_container_width=True,
                            on_click=cancel_sale,
                            args=(index,)
                        )

                    with cancel_col:
                        st.button(
                            "やめる",
                            key=f"abort_{record['id']}",
                            use_container_width=True,
                            on_click=lambda k=confirm_key:
                                st.session_state.update({k: False})
                        )

                else:
                    st.button(
                        "この販売を取り消す",
                        key=f"cancel_{record['id']}",
                        use_container_width=True,
                        on_click=lambda k=confirm_key:
                            st.session_state.update({k: True})
                    )


# 売上集計
# 取り消されていない記録だけを集計する
active_sales = [
    record
    for record in st.session_state.sales_history
    if not record.get("cancelled", False)
]

sales = sum(record["price"] for record in active_sales)

product_counts = {
    product: 0 for product in products
}

set_counts = {
    1: 0,
    2: 0,
    4: 0
}

for record in active_sales:
    set_counts[record["pack_size"]] += 1

    for product, count in record["quantities"].items():
        if product in product_counts:
            product_counts[product] += count


st.divider()

st.subheader("現在の売上")

st.metric("売上金額", f"{sales:,}円")

st.subheader("商品別の販売本数")

for product, count in product_counts.items():
    st.write(f"{product}：{count}本")

st.subheader("販売方法別のセット数")

for size, count in set_counts.items():
    st.write(f"{size}本セット：{count}セット")

total_bottles = sum(product_counts.values())
total_sets = sum(set_counts.values())

st.write(f"販売本数の合計：{total_bottles}本")
st.write(f"販売セット数の合計：{total_sets}セット")