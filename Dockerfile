FROM python:3.11-slim

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Create working directory
WORKDIR /app

# Improved installation with better retry mechanism
RUN set -eux; \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /etc/apt/apt.conf.d && \
    echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/10no-check-valid-until && \
    echo 'APT::Get::Assume-Yes "true";' > /etc/apt/apt.conf.d/90assume-yes && \
    echo 'APT::Get::AllowUnauthenticated "true";' > /etc/apt/apt.conf.d/99allow-unauth && \
    echo 'Acquire::http::Pipeline-Depth "0";' > /etc/apt/apt.conf.d/99reduce-network-load && \
    echo 'Acquire::http::Timeout "60";' > /etc/apt/apt.conf.d/99timeout-settings && \
    echo 'Acquire::Languages "none";' > /etc/apt/apt.conf.d/99translations && \
    # Multiple retry attempts for apt-get update
    for i in $(seq 1 5); do \
        echo "Attempt $i of 5 for apt-get update"; \
        apt-get update --allow-releaseinfo-change --allow-weak-repositories \
            -o Acquire::AllowInsecureRepositories=true \
            -o Acquire::AllowDowngradeToInsecureRepositories=true \
            -o Acquire::CompressionTypes::Order::=gz \
            -o Acquire::Check-Valid-Until=false \
            -o APT::Get::AllowUnauthenticated=true && break || \
        { echo "Update failed, cleaning and retrying in 10 seconds..."; \
          apt-get clean; \
          rm -rf /var/lib/apt/lists/*; \
          sleep 10; }; \
    done && \
    # Multiple retry attempts for apt-get install
    for i in $(seq 1 5); do \
        echo "Attempt $i of 5 for apt-get install"; \
        apt-get install -y --no-install-recommends --allow-unauthenticated \
            --allow-downgrades --allow-change-held-packages \
            -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
            -o Acquire::Retries=3 \
            build-essential && break || \
        { echo "Install failed, cleaning and retrying in 10 seconds..."; \
          apt-get clean; \
          apt-get --fix-broken install -y; \
          rm -rf /var/lib/apt/lists/*; \
          sleep 10; }; \
    done && \
    # Final cleanup
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy only the pyproject.toml file first to leverage Docker cache
COPY pyproject.toml ./

# Install Poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Copy the rest of the application
COPY . .

# Expose ports for Dagster and Streamlit
EXPOSE 3000 8501

# Set the default command to run Dagster
CMD ["dagster", "dev"] 