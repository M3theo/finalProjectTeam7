docker build -t team7-secure .
docker run -d --name team7 -p 127.0.0.1:5000:5000 \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges \
  --memory 256m --pids-limit 100 -v team7-data:/app/instance team7-secure
