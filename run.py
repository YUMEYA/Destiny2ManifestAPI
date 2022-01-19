if __name__ == "__main__":
    import os
    import uvicorn
    from destiny2_manifest_api.tasks import scheduler

    uvicorn.run(
        "destiny2_manifest_api.asgi:app",
        host=os.getenv("APP_HOST", "localhost"),
        port=int(os.getenv("APP_PORT", "5000")),
        log_level="debug",
        reload=True,
    )
    scheduler.start()
