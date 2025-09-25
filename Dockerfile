FROM golang:1.22 AS build
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /bin/raalisence ./cmd/raalisence


FROM gcr.io/distroless/base-debian12
COPY --from=build /bin/raalisence /raalisence
COPY config.example.yaml /etc/raalisence/config.yaml
EXPOSE 8080
ENTRYPOINT ["/raalisence"]