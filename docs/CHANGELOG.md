# Changelog

All notable changes to the Advanced Crypto Trading Bot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Phase 2 - Data Pipeline Implementation

#### Added - 2025-01-20

- **Data Pipeline Infrastructure**
  - `DataCollector` class for fetching OHLCV data from Binance API
  - Batch collection support for multiple symbols and timeframes
  - Parallel processing with asyncio for improved performance
  - Parquet file backup storage

- **Database Enhancement**
  - New `price_data` table in Supabase for storing OHLCV data
  - Optimized indexes for time-series queries
  - Unique constraints to prevent duplicate data

- **Supabase Integration**
  - Batch upsert functionality with 1000 records per batch
  - Error handling that allows pipeline to continue on failures
  - Progress logging for batch operations

- **Testing Suite**
  - 9 comprehensive unit tests for data pipeline
  - Integration tests for data flow validation
  - Functional test script for real API testing

- **Documentation**
  - Phase 2 implementation guide (`docs/PHASE2_IMPLEMENTATION.md`)
  - Updated database schema documentation
  - Enhanced API documentation

#### Changed

- Extended `backend/data_pipeline/collector.py` with Supabase save functionality
- Updated `docs/DATABASE_SCHEMA.md` with Phase 2 table definitions

#### Technical Details

- SQLAlchemy ORM model for `price_data` table
- Decimal precision (20,8) for cryptocurrency prices
- Timezone-aware timestamps for global market data

---

## [0.2.0] - 2025-01-18

### Phase 1 Completion - Project Restructuring

#### Added

- Organized documentation structure in `docs/` directory
- Comprehensive documentation index (`docs/README.md`)

#### Changed

- Moved all documentation files from root to `docs/`
- Updated all cross-references in documentation files
- Preserved git history with `git mv` commands

#### Removed

- Scattered markdown files from project root (except README.md and LICENSE)

---

## [0.1.0] - 2025-01-15

### Initial Release - Phase 1 Foundation

#### Added

- **Backend Infrastructure**
  - FastAPI application with modular architecture
  - Supabase database integration
  - JWT authentication system
  - RESTful API endpoints

- **Frontend Application**
  - Next.js 13+ with App Router
  - Tailwind CSS styling
  - Responsive design
  - Real-time chart components

- **Core Features**
  - User authentication (login/register)
  - Strategy management
  - Portfolio tracking
  - Basic backtesting

- **Development Tools**
  - Docker containerization
  - GitHub Actions CI/CD
  - Pre-commit hooks
  - Comprehensive test suite

---

## Upcoming Releases

### [0.3.0] - Phase 2 Completion (Planned)

- Real-time WebSocket price updates
- Enhanced backtesting with real data
- API endpoints using live market data
- Performance optimizations

### [0.4.0] - Phase 3 (Planned)

- Machine learning integration
- Advanced trading strategies
- Risk management system
- Multi-exchange support

---

**Note**: Dates are in YYYY-MM-DD format. For detailed commit history, see [GitHub commits](https://github.com/shingo25/advanced-crypto-trading-bot/commits/main).
