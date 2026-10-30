import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

connection = None
test_id = None

try:
    connection = psycopg2.connect(database_url)
    cursor = connection.cursor()

    # テスト用の販売記録を保存する
    cursor.execute(
        """
        INSERT INTO public.sales_history
            (pack_size, price, quantities)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (1, 120, Json({"テスト用": 1}))
    )

    test_id = cursor.fetchone()[0]
    connection.commit()
    print(f"保存成功！ ID: {test_id}")

    # 保存した記録を読み出す
    cursor.execute(
        """
        SELECT id, pack_size, price, quantities, cancelled
        FROM public.sales_history
        WHERE id = %s
        """,
        (test_id,)
    )

    record = cursor.fetchone()
    print("読み出したデータ：")
    print(record)

    # テスト用の記録だけを削除する
    cursor.execute(
        "DELETE FROM public.sales_history WHERE id = %s",
        (test_id,)
    )
    connection.commit()

    print("削除成功！")
    print("保存・読み出し・削除のテストが完了したよ！")

except Exception as error:
    if connection is not None:
        connection.rollback()
    print("テスト中にエラーが発生したよ。")
    print(error)

finally:
    if connection is not None:
        connection.close()