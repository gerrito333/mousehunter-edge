#!/bin/bash

directory="/home/pi/PycharmProjects/mausjaeger/images"
threshold=1
# Get the number of files in the directory
num_files=$(ls -1 "$directory" | wc -l)
echo "number of files: $num_files"
if (( num_files > threshold ));
  then        
    # Delete all files in the directory
    rm -f "$directory"/*

    # Restart the imagewatcher and mausjaeger services
    sudo systemctl restart imagewatcher.service mausjaeger.service
    echo "Deleted $num_files files and restarted services."
  else
    echo "No files to delete."
  fi

