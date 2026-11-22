docker build --target test -t team7-test .
docker run --rm --read-only --tmpfs /tmp --cap-drop ALL --network none team7-test
