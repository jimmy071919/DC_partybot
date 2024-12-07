#!/bin/bash

# 下載 FFmpeg 靜態二進制文件
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz

# 解壓縮
tar -xf ffmpeg-release-i686-static.tar.xz

# 找到解壓後的資料夾（通常包含版本號）
FFMPEG_FOLDER=$(ls | grep ffmpeg-release-i686-static)

# 賦予執行權限
chmod +x ./$FFMPEG_FOLDER/ffmpeg

# 將 FFmpeg 複製到專案根目錄
cp ./$FFMPEG_FOLDER/ffmpeg ./ffmpeg

# 清理下載的壓縮檔
rm ffmpeg-release-i686-static.tar.xz

# 顯示 FFmpeg 版本
./ffmpeg -version
