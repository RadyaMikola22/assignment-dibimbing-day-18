import pyspark
import os
from dotenv import load_dotenv
from pathlib import Path
import pyspark.sql.functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType

dotenv_path = Path("/opt/app/.env")
load_dotenv(dotenv_path=dotenv_path)

spark_hostname = os.getenv("SPARK_MASTER_HOST_NAME")
spark_port = os.getenv("SPARK_MASTER_PORT")
kafka_host = os.getenv("KAFKA_HOST")
kafka_topic = os.getenv("KAFKA_TOPIC_NAME")

spark_host = f"spark://{spark_hostname}:{spark_port}"

os.environ[
    "PYSPARK_SUBMIT_ARGS"
] = "--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.2 org.postgresql:postgresql:42.2.18"

sparkcontext = pyspark.SparkContext.getOrCreate(
    conf=(pyspark.SparkConf().setAppName("DibimbingStreaming").setMaster(spark_host))
)
sparkcontext.setLogLevel("WARN")
spark = pyspark.sql.SparkSession(sparkcontext.getOrCreate())

# Skema untuk data JSON dalam kolom 'value'
json_schema = StructType([
    StructField("order_id", StringType(), True),
    StructField("customer_id", IntegerType(), True),
    StructField("furniture", StringType(), True),
    StructField("color", StringType(), True),
    StructField("price", IntegerType(), True),
    StructField("ts", TimestampType(), True)
])

stream_df = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", f"{kafka_host}:9092")
    .option("subscribe", kafka_topic)
    .option("startingOffsets", "latest")
    .load()
)

# Parse kolom 'value' sebagai data JSON
parsed_stream_df = stream_df.selectExpr("CAST(value AS STRING)").withColumn("value", F.from_json("value", json_schema))

# Pilih kolom-kolom yang ada pada value
selected_columns_df = parsed_stream_df.select("value.order_id", "value.customer_id", "value.furniture", "value.color", "value.price", "value.ts")

(
    selected_columns_df
    .select(
        selected_columns_df["ts"].alias("Timestamp"), 
        selected_columns_df["price"].alias("RunningTotal")
        )
    .writeStream.format("console")
    .outputMode("append")
    .start()
    .awaitTermination()
)
