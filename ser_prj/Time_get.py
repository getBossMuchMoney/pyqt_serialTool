from datetime import datetime


def get_DataFileName():
    current_date = datetime.now()
    filename = (
        "DataFile_" + (str(current_date))[0:10] + "_" + (str(current_date))[11:19]
    ).replace(":", "-")
    return filename


def get_strTime():
    timestr = (str(datetime.now()))[11:23]
    return timestr
