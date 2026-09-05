# Library Information System — Phased Development Plan

## Overview

Modular Odoo 19 Community LIS built one addon at a time. Each phase: implement → test on `odoo_lis_test` → user approves → next.

**Test DB:** `odoo_lis_test`
**Addons path:** `custom_addons/`
**Dev server:** `./start-odoo.sh -d odoo_lis_test -u <module> --http-port=8069`

---

## Phase 0 — `library_base` (App Shell + Branch/Location Hierarchy)

**Status:** COMPLETE

| Item | Detail |
|------|--------|
| App entry | Top-level "Library Management" menu (`application: True`) |
| Models | `library.branch`, `library.floor`, `library.section`, `library.shelf`, `library.weekday` |
| User extension | `res.users.allowed_branch_ids` (Many2many) |
| Security | Privilege group, 10 role groups, record rules, ACLs |
| Features | Code auto-generation (ir.sequence), coordinate validation, working hours validation |
| Warehouse | `warehouse_id` on branch (depends on `stock`) |
| Tests | 12 automated tests passing |

---

## Phase 1 — `library_catalog` (Books + Authors + Publishers)

| Item | Detail |
|------|--------|
| Models | `library.book`, `library.book.copy`, `library.author`, `library.publisher`, `library.subject`, `library.category`, `library.language`, `library.classification.system`, `library.classification.code`, `library.series` |
| Book fields | name, subtitle, isbn_10, isbn_13, edition, publication_year, author_ids, publisher_id, language_id, category_ids, subject_ids, classification_id, description, page_count, cover_image, book_type, product_id |
| Copy fields | book_id, copy_number, barcode, qr_code, branch_id, floor_id, section_id, shelf_id, acquisition_date, acquisition_cost, condition, state, stock_lot_id, reference_only, circulating |
| Copy states | available, reserved, on_loan, in_transit, processing, repair, damaged, lost, missing, withdrawn, reference_only |
| Barcode | Unique per copy (e.g. `LIB01-BK-000001`) |
| QR code | Internal identifier (`LIBCOPY:123456`) |
| book_type | Book, Reference Book, Journal, Magazine, Thesis, Research Paper, Audio Book, E-Book, Other |
| Depends | `library_base`, `product` |

---

## Phase 2 — `library_membership` (Members + Plans)

| Item | Detail |
|------|--------|
| Models | `library.member`, `library.membership.plan` |
| Member fields | member_number, partner_id, membership_plan_id, registration_date, expiry_date, branch_id, member_type, status, barcode, max_books, current_loans_count, outstanding_fines, blocked, block_reason |
| Plan fields | name, duration, membership_fee, maximum_books, loan_period_days, maximum_renewals, reservation_limit, fine_per_day, maximum_fine, grace_period_days |
| Member types | Adult, Child, Student, University Student, Faculty, Employee, Researcher, VIP, Organization |
| Status | draft, active, expired, suspended, blocked, cancelled |
| Card | Printable library card with name, number, photo, barcode, QR, expiry |
| Depends | `library_base` |

---

## Phase 3 — `library_circulation` (Loans + Returns + Renewals + Fines)

| Item | Detail |
|------|--------|
| Models | `library.loan`, `library.loan.line`, `library.fine` |
| Loan fields | name, member_id, branch_id, issue_date, due_date, return_date, issued_by, returned_by, state |
| Loan line fields | loan_id, book_copy_id, issue_datetime, due_datetime, return_datetime, renewal_count, fine_amount, condition_on_issue, condition_on_return |
| Fine fields | member_id, loan_line_id, fine_type, amount, paid_amount, remaining_amount, state |
| Fine types | Late Return, Lost Book, Damaged Book, Membership, Other |
| Due date engine | Based on membership plan + book type + category + branch policy + holiday calendar |
| Borrowing validation | Membership active, not blocked, fines within limit, book available, etc. |
| Depends | `library_base`, `library_catalog`, `library_membership` |

---

## Phase 4 — `library_reservation` (Hold Queue)

| Item | Detail |
|------|--------|
| Model | `library.reservation` |
| Fields | member_id, book_id, preferred_branch_id, request_date, priority, queue_position, copy_id, ready_date, expiry_date, state |
| States | waiting, allocated, ready_for_pickup, collected, expired, cancelled |
| Hold shelf | Allocated copy held for configurable period (e.g. 3 days) |
| Depends | `library_base`, `library_catalog`, `library_membership` |

---

## Phase 5 — `library_inventory` (Stock Integration)

| Item | Detail |
|------|--------|
| Stock structure | Branch warehouses with internal locations (Processing, Available, Hold Shelf, Repair, Withdrawn) |
| Copy ↔ Stock | `library.book` → `product.product`, `library.book.copy` → `stock.lot` |
| Features | Traceability, transfers, procurement, stock history |
| Inter-branch transfer | Requested → Approved → Prepared → In Transit → Received → Completed |
| Depends | `library_base`, `library_catalog`, `stock` |

---

## Phase 6 — `library_acquisition` (Procurement)

| Item | Detail |
|------|--------|
| Flow | Librarian Request → Approval → Purchase → Vendor → Receive → Catalog → Generate Copies → Barcodes → Shelf Assignment |
| Model | `library.purchase.request` (member book requests) |
| Depends | `library_base`, `library_catalog`, `purchase` |

---

## Phase 7 — `library_serials` (Periodicals)

| Item | Detail |
|------|--------|
| Models | `library.subscription`, `library.serial.issue` |
| Subscription fields | title, supplier_id, start_date, end_date, frequency, expected_next_issue, branch_id, cost |
| Issue status | expected, received, missing, claimed |
| Depends | `library_base` |

---

## Phase 8 — `library_digital` (E-Books + Audio)

| Item | Detail |
|------|--------|
| Features | E-Books, PDF, Audio Books, Research Documents, Digital Journals |
| Permissions | Access permissions, download permission, license limit, expiry |
| Depends | `library_base` |

---

## Phase 9 — `library_events` (Library Programs)

| Item | Detail |
|------|--------|
| Models | `library.event`, `library.event.registration` |
| Event types | Book Club, Workshop, Children Story Session, Training, Author Meeting, Reading Competition |
| Depends | `library_base` |

---

## Phase 10 — `library_offline_map` (Geographic + Indoor Maps)

| Item | Detail |
|------|--------|
| Tech | MapLibre GL JS, local vector tiles, PMTiles |
| Services | Local Nominatim (geocoding), Valhalla (routing) |
| Features | Branch pins, nearest library, offline geocoding/reverse geocoding/routing |
| Indoor map | SVG floor plans with interactive OWL components |
| Shelf mapping | `library.shelf` → map_x, map_y, map_width, map_height |
| Depends | `library_base` |

---

## Phase 11 — `library_mobile` (Bookmobile)

| Item | Detail |
|------|--------|
| Models | `library.mobile.unit`, `library.mobile.route`, `library.mobile.stop`, `library.mobile.trip` |
| Trip flow | Prepare → Select Books → Internal Transfer → Start Route → Visit Stops → Issue/Return → Return Branch → Reconcile |
| Depends | `library_base`, `library_circulation` |

---

## Phase 12 — `library_portal` (Member Self-Service)

| Item | Detail |
|------|--------|
| Features | Search catalog, check availability, reserve, view loans, renew, view fines, view history, events, locations |
| Depends | `library_base`, `library_catalog`, `library_membership`, `library_circulation`, `portal` |

---

## Phase 13 — `library_notifications` (Alerts + Reminders)

| Item | Detail |
|------|--------|
| Notifications | Book Due Soon, Book Overdue, Reservation Ready, Reservation Expiring, Membership Expiring, Fine Created, Event Reminder, Requested Book Available |
| Channels | Odoo Notification, Email; Optional: SMS, WhatsApp |
| Depends | `library_base`, `mail` |

---

## Phase 14 — `library_audit` (Audit Trail)

| Item | Detail |
|------|--------|
| Features | Track all critical changes with user, timestamp, old/new values |
| Depends | `library_base`, `mail` |

---

## Phase 15 — `library_dashboard` (Dashboards)

| Item | Detail |
|------|--------|
| Features | Circulation stats, inventory overview, membership analytics, overdue tracking |
| Depends | `library_base`, `web` |

---

## Phase 16 — `library_reports` (Print + Export)

| Item | Detail |
|------|--------|
| Features | Book catalog reports, circulation reports, inventory reports, member reports, fine reports |
| Depends | `library_base`, `web` |

---

## Phase 17 — `library_integration` (Glue + Final Wiring)

| Item | Detail |
|------|--------|
| Features | Cross-module integration, POS integration (optional), final data hooks, API endpoints |
| Depends | All library modules |

---

## Odoo Core Modules Used

| Module | Purpose |
|--------|---------|
| `base` | Foundation |
| `mail` | Chatter, tracking, notifications |
| `contacts` | Partner management |
| `product` | Product template for books |
| `stock` | Warehouse, lots, transfers |
| `purchase` | Procurement |
| `account` | Invoicing fines/fees |
| `portal` | Member self-service |
| `web` | Web client, dashboards |
| `hr` | Staff management |
| `barcodes` | Barcode scanning |
| `point_of_sale` | Optional POS integration |
