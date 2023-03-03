r"""
 Use DataFrames and SQL to count words in UTF8 encoded, '\n' delimited text received from the
 network every second.

 Usage: sql_network_wordcount.py <hostname> <port>
   <hostname> and <port> describe the TCP server that Spark Streaming would connect to receive data.

 To run this on your local machine, you need to first run a Netcat server
    `$ nc -lk 9999`
 and then run the example
    `$ bin/spark-submit examples/src/main/python/streaming/sql_network_wordcount.py localhost 9999`
"""
from __future__ import print_function

import sys

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.sql import Row, SparkSession


def getSparkSessionInstance(sparkConf):
    if ('sparkSessionSingletonInstance' not in globals()):
        globals()['sparkSessionSingletonInstance'] = SparkSession\
            .builder\
            .config(conf=sparkConf)\
            .getOrCreate()
    return globals()['sparkSessionSingletonInstance']


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: sql_network_wordcount.py <hostname> <port> ", file=sys.stderr)
        sys.exit(-1)
    host, port = sys.argv[1:]
    sc = SparkContext(appName="PythonSqlNetworkWordCount")
    ssc = StreamingContext(sc, 1)

    # Create a socket stream on target ip:port and count the
    # words in input stream of \n delimited text (eg. generated by 'nc')
    lines = ssc.socketTextStream(host, int(port))
    words = lines.flatMap(lambda line: line.split(" "))

    # Convert RDDs of the words DStream to DataFrame and run SQL query
    def process(time, rdd):
        print("========= %s =========" % str(time))

        try:
            # Get the singleton instance of SparkSession
            spark = getSparkSessionInstance(rdd.context.getConf())

            # Convert RDD[String] to RDD[Row] to DataFrame
            rowRdd = rdd.map(lambda w: Row(word=w))
            wordsDataFrame = spark.createDataFrame(rowRdd)

            # Creates a temporary view using the DataFrame.
            wordsDataFrame.createOrReplaceTempView("words")

            # Do word count on table using SQL and print it
            wordCountsDataFrame = \
                spark.sql("select word, count(*) as total from words group by word")
            wordCountsDataFrame.show()
        except:
            pass

    words.foreachRDD(process)
    ssc.start()
    ssc.awaitTermination()
