# **Library Management & Offline Mapping System** 

## **Odoo 19 Community** 

**Platform:** Odoo 19 Community **System Type:** Library Information System — LIS **Architecture:** Modular Odoo Add-ons + Offline Mapping Services **Languages:** Arabic / English / RTL **Deployment:** On-Premise / LAN / Fully Offline Capable **Target:** Public Libraries / University Libraries / School Libraries / Multi-Branch Library Networks 

# **1. Project Vision** 

إنشاء نظام متكامل إلدارة شبكة مكتبات باستخدام Odoo 19 Community يغطي دورة الكتاب والمستفيد من لحظة شراء الكتاب وتسجيله وحىت اإلعارة واإلرجاع والحجز والجرد والنقل بني الفروع. 

النظام يجب أن يدعم: 

- Multi-Branch Libraries • Book Catalog • Authors / Publishers • Physical Book Copies • Members • Membership Plans • Borrowing • Return • Renewals • Reservations • Waiting Lists • Fines • Lost / Damaged Books • Stock & Branch Transfers 

- Procurement • Periodicals • Digital Resources • Library Events • Offline Geographic Map • Indoor Library Map • Mobile Library / Bookmobile • Member Portal • Dashboards 

- Reports 

- Notifications 

1 

- Audit Trail 

- Barcode / QR Code 

- Arabic / English 

# **2. Core Architectural Principle** 

لن يتم بناء النظام داخل Module .واحدة ضخمة 

سيتم تقسيمه إلى: 

```
library_base
library_catalog
library_membership
library_circulation
library_reservation
library_inventory
library_acquisition
library_serials
library_digital
library_events
library_offline_map
library_mobile
library_portal
library_notifications
library_audit
library_dashboard
library_reports
library_integration
```

# **3. Odoo Core Usage** 

ال نعيد اخرتاع الوظائف الموجودة في Odoo. 

نستخدم: 

```
base
mail
contacts
product
stock
purchase
```

2 

```
account
portal
web
hr
barcodes
```

Optional: 

```
point_of_sale
```

إذا كانت المكتبة تقوم ببيع كتب أو أدوات مكتبية بجانب اإلعارة. 

# **4. High-Level Architecture** 



<!-- Start of picture text -->
                       Odoo 19 Community<br>                              │<br>         ┌────────────────────┼─────────────────────┐<br>         │                    │                     │<br>         ▼                    ▼                     ▼<br>    Library Core         Odoo Business        Offline Maps<br>                         Applications<br>         │                    │                     │<br>         │                    │                     │<br> Catalog / Members       Stock / Purchase      MapLibre<br> Loans / Reservations    Accounting / POS      Local Tiles<br>         │                                      Nominatim<br>         │                                      Valhalla<br>         ▼<br>   Portal / Reports<br><!-- End of picture text -->

# **5. Organization Structure** 

النظام يدعم أكرث من مكتبة وأكرث من فرع. 

```
Library Organization
```

```
       │
       ├── Branch
       │     │
       │     ├── Floor
```

3 

```
       │     │     │
       │     │     ├── Section
       │     │     │     │
       │     │     │     ├── Shelf
       │     │     │     └── Shelf
       │     │
       │     ├── Reading Area
       │     ├── Kids Area
       │     ├── Reference Area
       │     └── Store
       │
       └── Branch
```

Models: 

```
library.branch
library.floor
library.section
library.shelf
```

# **6. Library Branch** 

Model: 

```
library.branch
```

Fields: 

```
name
code
company_id
manager_id
```

```
phone
email
street
city
state_id
country_id
```

4 

```
latitude
longitude
warehouse_id
opening_time
closing_time
working_day_ids
active
```

# **7. Book Architecture** 

أهم قرار في الـData Model: 

ال نعترب الكتاب والنسخة الفعلية نفس الـrecord. 

مثال: 

كتاب: 

```
Clean Code
Robert C. Martin
ISBN 9780132350884
```

يوجد منه: 

```
20 Copies
```

إذن لدينا: 

```
Bibliographic Record
        │
        ├── Copy #001
        ├── Copy #002
        ├── Copy #003
        └── ...
```

5 

# **8. Catalog Module** 

Module: 

```
library_catalog
```

Models: 

```
library.book
library.book.copy
library.author
library.publisher
library.subject
library.category
library.language
library.classification
library.series
```

# **9. Book / Bibliographic Record** 

Model: 

```
library.book
```

يمثل Title / Edition .وليس النسخة الموجودة على الرف 

Fields: 

```
name
subtitle
isbn_10
isbn_13
edition
```

6 

```
publication_year
author_ids
publisher_id
language_id
category_ids
subject_ids
classification_id
classification_code
description
page_count
cover_image
book_type
product_id
active
```

book_type: 

```
Book
Reference Book
Journal
Magazine
Thesis
Research Paper
Audio Book
E-Book
Other
```

# **10. Author** 

```
library.author
```

Fields: 

7 

```
name
birth_date
death_date
country_id
biography
image
website
```

يدعم Many2Many  ألن الكتاب يمكن أن يكون له أكرث من Author. 

# **11. Publisher** 

```
library.publisher
```

Fields: 

```
name
partner_id
country_id
website
active
```

# **12. Classification** 

النظام ال يعتمد على Category .فقط 

يدعم Classification System. 

مثال: 

```
Dewey Decimal Classification
Local Classification
University Classification
```

Models: 

8 

```
library.classification.system
library.classification.code
```

مثال: 

```
000 Computer Science
100 Philosophy
200 Religion
300 Social Sciences
...
```

# **13. Physical Book Copy** 

Model: 

```
library.book.copy
```

يمثل النسخة الفعلية الموجودة في المكتبة. 

Fields: 

```
book_id
```

```
copy_number
```

```
barcode
qr_code
branch_id
floor_id
section_id
shelf_id
```

```
acquisition_date
acquisition_cost
```

```
condition
```

```
state
```

9 

```
stock_lot_id
reference_only
circulating
last_inventory_date
```

# **14. Copy States** 

```
available
reserved
on_loan
in_transit
processing
repair
damaged
lost
missing
withdrawn
reference_only
```

يجب أال يستطيع Developer تغيري الحالة مباشرة بأي <mark>`write()`</mark> عشوائي. 

يتم التغيري من خالل Business Methods. 

# **15. Barcode Strategy** 

كل نسخة تحصل على Barcode .فريد 

مثال: 

10 

```
CAI-00000001
CAI-00000002
```

أو: 

```
LIB01-BK-000001
```

Barcode :يستخدم في 

```
Issue
Return
Inventory
Transfer
Book Search
Shelf Check
```

# **16. QR Code** 

يمكن أيضاً إنشاء QR Code. 

يحتوي فقط على Identifier :داخلي مثل 

```
LIBCOPY:123456
```

وال نضع معلومات شخصية أو معلومات طويلة بداخله. 

# **17. Member Management** 

Module: 

```
library_membership
```

ال نحول <mark>`res.partner`</mark> نفسه إلى Membership Record. 

نستخدم: 

11 

```
library.member
      │
      └── partner_id → res.partner
```

# **18. Member** 

Model: 

```
library.member
```

Fields: 

```
member_number
partner_id
membership_plan_id
registration_date
expiry_date
branch_id
member_type
status
barcode
max_books
current_loans_count
outstanding_fines
blocked
block_reason
```

12 

# **19. Member Types** 

Configurable. 

مثال: 

```
Adult
Child
Student
University Student
Faculty
Employee
Researcher
VIP
Organization
```

# **20. Membership Plan** 

```
library.membership.plan
```

Fields: 

```
name
```

```
duration
membership_fee
maximum_books
loan_period_days
maximum_renewals
```

13 

```
reservation_limit
fine_per_day
maximum_fine
grace_period_days
```

# **21. Membership Status** 

```
draft
active
expired
suspended
blocked
cancelled
```

# **22. Member Card** 

يمكن طباعة: 

```
Library Card
```

يحتوي: 

```
Member Name
```

```
Member Number
```

```
Photo
```

```
Barcode
```

14 

```
QR Code
Expiry Date
```

# **23. Circulation Module** 

Module: 

```
library_circulation
```

Models: 

```
library.loan
library.loan.line
```

# **24. Loan** 

```
library.loan
```

يمثل عملية إعارة. 

Fields: 

```
name
```

```
member_id
```

```
branch_id
```

```
issue_date
```

```
due_date
```

```
return_date
```

```
issued_by
```

```
returned_by
```

15 

```
state
```

# **25. Loan Lines** 

```
library.loan.line
```

Fields: 

```
loan_id
book_copy_id
issue_datetime
due_datetime
return_datetime
renewal_count
fine_amount
condition_on_issue
condition_on_return
```

# **26. Loan Workflow** 

```
Member
```

```
   ↓
Scan Member Card
   ↓
Check Membership
```

```
   ↓
Scan Book
   ↓
Validate Rules
   ↓
```

16 

```
Issue Book
   ↓
Due Date Calculation
   ↓
Book → On Loan
```

# **27. Borrowing Validation** 

قبل إصدار الكتاب يتم التأكد من: 

```
Membership active?
Membership expired?
Member blocked?
Outstanding fines over allowed limit?
Maximum books exceeded?
Book available?
Book reference-only?
Book reserved for another member?
Member allowed this category?
Age restriction?
```

إذا Rule :غري مستوفاة 

```
Issue is blocked
```

إال لو توجد Override Permission .لمسوؤول الفرع 

# **28. Due Date Engine** 

Due Date  ال يتم hard-code. 

17 

يحسب حسب: 

```
Membership Plan
Book Type
Book Category
Branch Policy
Holiday Calendar
```

مثال: 

```
Normal Book → 14 days
Reference Book → Cannot Borrow
Magazine → 7 days
Faculty Member → 30 days
```

# **29. Return Workflow** 

```
Scan Book
   ↓
Find Active Loan
   ↓
Calculate Delay
   ↓
Calculate Fine
   ↓
Check Book Condition
   ↓
Return
   ↓
Check Reservation Queue
```

إذا ال يوجد حجز: 

18 

```
Available
```

إذا يوجد حجز: 

```
Reserved / Hold Shelf
```

# **30. Renewal** 

Flow: 

```
Active Loan
     ↓
Request Renewal
     ↓
Validate
     ↓
New Due Date
```

Cannot Renew when: 

```
Another member reserved the book
```

```
Renewal limit reached
Membership expired
Member blocked
```

# **31. Reservation Module** 

```
library_reservation
```

Model: 

```
library.reservation
```

19 

# **32. Reservation** 

Fields: 

```
member_id
book_id
preferred_branch_id
request_date
priority
queue_position
copy_id
ready_date
expiry_date
state
```

# **33. Reservation States** 

```
waiting
allocated
ready_for_pickup
collected
expired
cancelled
```

20 

# **34. Waiting List** 

لو الكتاب كله مستعار: 

```
Book
 ↓
Reservation Queue
 ↓
Member #1
Member #2
Member #3
```

عند عودة Copy: 

```
Allocate → Member #1
```

ويرسل Notification. 

# **35. Hold Shelf** 

عند تخصيص كتاب لعضو: 

```
Reserved Copy
```

### يتم وضعه في: 

```
Hold Shelf
```

لفرتة مثل: 

```
3 days
```

إذا لم يحضر العضو: 

```
Reservation → Expired
```

وينتقل للعضو التالي. 

21 

# **36. Fine Engine** 

Fines  تكون configurable. 

مثال: 

```
1 EGP / day
```

أو: 

```
5 EGP / day
```

حسب Membership / Book Category. 

# **37. Fine Model** 

```
library.fine
```

Fields: 

```
member_id
loan_line_id
```

```
fine_type
```

```
amount
```

```
paid_amount
remaining_amount
```

```
state
```

fine_type: 

```
Late Return
```

22 

```
Lost Book
Damaged Book
Membership
Other
```

# **38. Fine Calculation** 

مثال: 

```
Due Date = 01/09
Returned = 06/09
Delay = 5 days
Fine Rate = 2 EGP
Fine = 10 EGP
```

### مع دعم: 

```
Grace Period
Maximum Fine
Holiday Exclusion
Manual Waiver
```

# **39. Fine Waiver** 

ال يتم حذف Fine. 

يكون: 

23 

```
Waived
```

مع: 

```
waived_by
waived_at
reason
```

# **40. Lost Book** 

Workflow: 

```
On Loan
   ↓
Reported Lost
   ↓
Replacement / Fine
   ↓
Financial Settlement
   ↓
Closed
```

Copy State: 

```
lost
```

# **41. Damaged Book** 

Damage Levels: 

```
Minor
Repairable
Major
```

24 

```
Destroyed
```

Workflow: 

```
Return
 ↓
Damage Assessment
 ↓
Repair
```

أو: 

```
Withdraw
```

# **42. Inventory Integration** 

Module: 

```
library_inventory
```

نستخدم Odoo Stock :إلدارة 

```
Branch Warehouses
Internal Locations
Transfers
Receipts
```

# **43. Stock Structure** 

مثال: 

25 

```
Main Library Warehouse
```

```
LIB01
 ├── Processing
 ├── Available
 ├── Hold Shelf
 ├── Repair
 └── Withdrawn
```

وفرع آخر: 

```
LIB02
```

# **44. Book Copy + Stock Integration** 

يفضل: 

```
library.book
      ↓
product.product
```

### والنسخة: 

```
library.book.copy
      ↓
stock.lot
```

### بحيث نستفيد من: 

```
Traceability
```

```
Transfers
Procurement
Stock History
```

بدون استخدام Stock .كنظام إعارة 

26 

اإلعارة تبقى داخل: 

```
library.loan
```

# **45. Inter-Branch Transfer** 

مثال: 

```
Cairo Library
```

```
       ↓
Transfer
```

```
       ↓
Alex Library
```

Workflow: 

```
Requested
Approved
Prepared
In Transit
Received
Completed
```

Copy: 

```
available
→ in_transit
→ available
```

27 

# **46. Acquisition Module** 

```
library_acquisition
```

يدعم: 

```
Purchase Request
Book Request
Supplier
```

```
Purchase Order
Receipt
Cataloging
Copy Creation
```

# **47. Acquisition Flow** 

```
Librarian Request
```

```
       ↓
Approval
```

```
       ↓
Purchase
```

```
       ↓
Vendor
```

```
       ↓
Receive Books
```

```
       ↓
Catalog
```

```
       ↓
Generate Copies
```

```
       ↓
Generate Barcodes
```

```
       ↓
Shelf Assignment
```

28 

```
       ↓
Available
```

# **48. Member Book Request** 

يمكن للعضو طلب شراء كتاب غري موجود. 

Model: 

```
library.purchase.request
```

Fields: 

```
member_id
book_name
author
isbn
reason
request_date
state
```

States: 

```
submitted
under_review
approved
rejected
purchased
```

29 

# **49. Periodicals** 

Module: 

```
library_serials
```

إلدارة: 

```
Magazine
Journal
Newspaper
Academic Periodical
```

# **50. Subscription** 

```
library.subscription
```

Fields: 

```
title
supplier_id
start_date
end_date
frequency
expected_next_issue
branch_id
cost
```

30 

# **51. Issue Tracking** 

```
library.serial.issue
```

مثال: 

```
National Geographic
```

```
August 2026
Issue #08
```

Status: 

```
expected
received
missing
claimed
```

# **52. Digital Library** 

Module: 

```
library_digital
```

يدعم: 

```
E-Books
```

```
PDF
```

```
Audio Books
```

```
Research Documents
```

31 

```
Digital Journals
```

لكن يجب دعم: 

```
Access Permissions
Download Permission
License Limit
Expiry
```

# **53. Events** 

Module: 

```
library_events
```

لـ: 

```
Book Club
Workshop
Children Story Session
Training
Author Meeting
Reading Competition
```

Models: 

```
library.event
library.event.registration
```

32 

# **54. Offline Map Module** 

Module: 

```
library_offline_map
```

هذا Module مستقل تماماً عن الـCatalog/Circulation. 

# **55. Offline Map Goals** 

الخريطة تعمل بدون: 

```
Google Maps
Google API
Internet Connection
External CDN
External Tile Server
```

# **56. Offline Map Technology** 

Frontend: 

```
MapLibre GL JS
```

Map Data: 

```
Local Vector Tiles
```

Recommended storage: 

```
PMTiles
```

33 

أو: 



<!-- Start of picture text -->
MBTiles + Local Tile Server<br><!-- End of picture text -->

كل الملفات: 



<!-- Start of picture text -->
JS<br>CSS<br>Fonts<br>Sprites<br>Styles<br>Tiles<br><!-- End of picture text -->

تكون Local. 

# **57. Offline Deployment** 



<!-- Start of picture text -->
                Internal LAN<br>                     │<br>        ┌────────────┴─────────────┐<br>        │                          │<br>      Odoo                    Map Server<br>    :8069                       :8080<br>        │                          │<br>        │                          ├── Egypt Tiles<br>        │                          ├── Styles<br>        │                          ├── Fonts<br>        │                          └── Sprites<br>        │<br>        └──────── Browser ─────────┘<br><!-- End of picture text -->

Internet: 



<!-- Start of picture text -->
NOT REQUIRED<br><!-- End of picture text -->

34 

# **58. Offline Map Architecture — Recommended** 

Deployment: 

```
Docker / Linux Server
nginx
odoo19
postgresql
offline_map_service
optional_nominatim
optional_valhalla
```

Services: 

# **59. Geographic Map Features** 

الخريطة تعرض: 

```
Library Branches
Member Service Areas
Bookmobile Stops
Events
Delivery Locations
Partner Schools
Partner Universities
```

35 

# **60. Library Branch Pin** 

كل Branch تظهر كـPin. 

عند الضغط: 

```
Branch Name
Address
Working Hours
Available Books
Phone
Manager
Directions
```

# **61. Nearest Library** 

إذا لدينا إحداثيات المستخدم: 

```
Latitude
Longitude
```

يمكن حساب: 

```
Nearest Branch
```

بدون Internet. 

# **62. Offline Geocoding** 

إذا أردنا أن المستخدم يكتب: 

36 

```
Nasr City
```

ويجد المكان بدون Internet: 

يتم تشغيل: 

```
Nominatim
```

محليا. 

# **63. Offline Reverse Geocoding** 

User clicks: 

```
30.056...
31.330...
```

ب باستخدامالنظام يستطيع استخراج عنوان تقر Local Nominatim. 

# **64. Offline Routing** 

لو نحتاج: 

```
Current Position
```

```
       ↓
Library Branch
```

مع: 

```
Route
```

```
Distance
```

```
Estimated Time
```

يتم تشغيل: 

37 

```
Valhalla
```

داخل السريفر. 

# **65. No External API** 

Odoo :يتصل مثالً بـ 

```
http://map-router:8002/route
```

وليس: 

```
maps.google.com
```

# **66. Bookmobile** 

Module: 

```
library_mobile
```

للمكتبات المتنقلة. 

Models: 

```
library.mobile.unit
library.mobile.route
library.mobile.stop
library.mobile.trip
```

38 

# **67. Bookmobile Route** 

مثال: 

```
Mobile Library #1
Saturday Route
Library
 ↓
School A
 ↓
Village B
 ↓
Youth Center
 ↓
School C
 ↓
Library
```

# **68. Route Map** 

يعرض: 

```
Start
Stops
Route
Distance
Estimated Duration
```

كلها Offline. 

# **69. Bookmobile Inventory** 

كل سيارة ممكن تعامل كـ: 

39 

```
Stock Location
```

مثال: 

```
MOBILE-01/Books
```

ويتم Transfer .الكتب إليها 

# **70. Mobile Trip** 

```
Prepare Trip
 ↓
Select Books
 ↓
Internal Transfer
 ↓
Start Route
 ↓
Visit Stops
 ↓
Issue / Return Books
 ↓
Return Branch
 ↓
Reconcile Inventory
```

# **71. Indoor Library Map** 

مزية مهمة مختلفة عن Geographic Map. 

النظام يحتوي على: 

```
Floor Plan
```

لكل فرعً. 

مثال: 

40 

```
Ground Floor
```

مث: 

```
Section A
Shelf A01
Section A
Shelf A02
Kids Area
Reference Area
```

# **72. Find Book on Indoor Map** 

عند البحث عن: 

```
Clean Code
```

النظام يظهر: 

```
Available
```

```
Branch: Main Library
Floor: 1
Section: Computer Science
Shelf: CS-04
```

مث Button: 

```
Show On Map
```

تفتح Indoor Map  وتحدد Shelf. 

41 

# **73. Indoor Map Technology** 

ال يحتاج Internet إطالقا. 

يمكن استخدام: 

```
SVG Floor Plans
```

مع Interactive OWL Component. 

كل Shelf :يحصل على 

```
library.shelf
map_x
map_y
map_width
map_height
```

# **74. Search** 

Global Library Search :يدعم 

```
Title
```

```
ISBN
```

```
Author
```

```
Publisher
```

```
Subject
```

```
Category
```

```
Barcode
```

```
Classification Code
```

42 

```
Keyword
```

# **75. Search Result** 

مثال: 

```
Clean Code
Robert C. Martin
ISBN: ...
Available: 7 / 20
Main Library: 3
Nasr City: 2
Alexandria: 2
```

# **76. Availability** 

نفرق بني: 

```
Total Copies
Available Copies
On Loan
Reserved
Lost
Damaged
In Transit
```

43 

# **77. Member Portal** 

Module: 

```
library_portal
```

Member :يستطيع 

```
Search Catalog
Check Availability
Reserve Book
View Current Loans
View Due Dates
Renew Loan
View Fines
View Borrowing History
View Events
View Library Locations
```

# **78. Portal Offline Map** 

لو Portal  مستخدم داخل LAN: 

الخريطة تظل تعمل Offline :ألنها تستخدم نفس 

```
local map service
```

44 

# **79. Notifications** 

Notifications: 

```
Book Due Soon
Book Overdue
Reservation Ready
Reservation Expiring
Membership Expiring
Fine Created
Event Reminder
Requested Book Available
```

Channels: 

```
Odoo Notification
```

```
Email
```

Optional: 

```
SMS
```

```
WhatsApp
```

عند وجود Integration. 

# **80. Reminder Examples** 

```
3 Days Before Due
```

```
1 Day Before Due
```

45 

```
Due Today
```

```
3 Days Overdue
7 Days Overdue
14 Days Overdue
```

كلها Configurable. 

# **81. Security Roles** 

## **Library User** 

```
Library / User
```

## **Librarian** 

```
Library / Librarian
```

## **Circulation Officer** 

```
Library / Circulation Officer
```

## **Cataloger** 

```
Library / Cataloger
```

## **Acquisition** 

```
Library / Acquisition Officer
```

## **Inventory** 

```
Library / Inventory Officer
```

46 

## **Branch Manager** 

```
Library / Branch Manager
```

## **Network Manager** 

```
Library / Library Manager
```

## **Map** 

```
Library / Map Administrator
```

## **Administrator** 

```
Library / Administrator
```

# **82. Security Rules** 

مثال: 

Circulation Officer: 

```
Can:
```

```
Issue
Return
Renew
Reserve
View Member
Cannot:
Delete Catalog
Change Fine Rules
Modify Acquisition
```

Cataloger: 

47 

```
Can:
```

```
Books
Authors
Publishers
Classification
Copies
Cannot:
Take Payment
Modify Loans
```

# **83. Branch Access** 

كل User :يمكن تحديد 

```
allowed_branch_ids
```

مثال: 

```
Ahmed
Main Library
Nasr City Library
```

ويرى فقط بيانات هذه الفروع حسب Role. 

# **84. Audit** 

Module: 

```
library_audit
```

يسجل العمليات الحساسة: 

48 

```
Book Issued
Book Returned
Fine Waived
Book Lost
Book Deleted
Member Blocked
Membership Changed
Reservation Override
Stock Adjustment
Map Coordinates Changed
```

# **85. Delete Policy** 

ال يتم Delete :لـ 

```
Completed Loan
Fine
Historical Reservation
Stock Transaction
```

يتم: 

```
Cancel
Archive
Void
```

حسب العملية. 

49 

# **86. Dashboard** 

Module: 

```
library_dashboard
```

Main KPIs: 

```
Total Books
Total Copies
Available Copies
Books On Loan
Overdue Books
Reservations
Active Members
Expired Memberships
Lost Books
Damaged Books
Outstanding Fines
```

# **87. Circulation Dashboard** 

يعرض: 

```
Issued Today
Returned Today
```

```
Overdue
```

50 

```
Due Today
Reservations Ready
Average Loan Duration
```

# **88. Branch Dashboard** 

```
Branch Inventory
```

```
Members
Daily Loans
Daily Returns
Overdue
Lost Books
Occupancy / Visits
Events
```

# **89. Map Dashboard** 

يعرض Offline Map: 

```
All Branches
Mobile Units
Mobile Stops
Service Areas
```

Filters: 

51 

```
Branch
Region
Status
Library Type
```

# **90. Reports** 

Reports :تشمل 

```
Most Borrowed Books
Least Borrowed Books
Most Active Members
Overdue Report
Fine Report
Lost Books
Damaged Books
Member Growth
Loans By Branch
Loans By Category
Loans By Author
Inventory By Branch
Reservation Report
Acquisition Report
```

52 

# **91. Heatmap Reports** 

يمكن إنشاء: 

```
Borrowing by Hour
Borrowing by Day
Borrowing by Month
```

لتحديد ساعات الضغط. 

# **92. Geographic Reports** 

Map :يمكن تعرض 

```
Members Per Area
Branches
Mobile Library Coverage
Bookmobile Stops
```

لكن يجب مراعاة Privacy .وعدم عرض بيانات عضو فردية إال للصالحيات المصرح بها 

# **93. Optional Retail Sales** 

لو المكتبة تبيع كتب أيضا: 

Module: 

```
library_retail
```

يعتمد على: 

53 

```
point_of_sale
```

ويظل: 

```
Library Lending
```

مستقالً عن: 

```
Retail Sales
```

# **94. Book Sale** 

كتاب يمكن تحديد: 

```
can_be_borrowed
can_be_sold
```

لكن نسخة اإلعارة وStock  البيع يجب أن يكون بينهم Business Rules .واضحة 

# **95. Configuration** 

Configuration Menu: 

```
Branches
```

```
Floors
```

```
Sections
```

```
Shelves
```

```
Membership Plans
```

```
Member Types
Book Types
```

54 

```
Loan Policies
Fine Policies
Classification Systems
Languages
Map Configuration
Notification Rules
```

# **96. Critical Business Rules** 

قبل Development :يجب اعتماد 

## **Membership** 

```
Maximum Books
Loan Period
Fine Limits
Age Rules
Membership Expiry
```

## **Borrowing** 

```
Reference Books
Renewal Limits
Reservation Priority
Overdue Blocking
Fine Blocking
```

55 

## **Reservation** 

```
Queue Rule
Hold Days
Branch Pickup
Cross-Branch Reservation
```

## **Lost Books** 

```
Replacement Policy
Fine Calculation
Replacement Book
```

## **Maps** 

```
Required Geography
Zoom Level
Routing Required?
Geocoding Required?
Mobile Library Required?
```

# **97. Offline Map Data Strategy** 

ال يتم تحميل خريطة العالم بالكامل إذا المشروع داخل مصر فقطً. 

مثال: 

```
Egypt
```

أو: 

56 

```
Cairo
Giza
Alexandria
Delta
Upper Egypt
```

حسب نطاق المشروع. 

هذا يوفر: 

```
Disk Space
RAM
Map Loading
Routing Performance
```

# **98. Air-Gapped Environment** 

إذا السريفر لن يتصل باإلنرتنت نهائيا: 

Map Update :يتم كاآلتي 

```
Admin Computer With Internet
       ↓
Download New Map Dataset
       ↓
Validate
       ↓
Copy Using Secure Medium
       ↓
Upload To Library Server
       ↓
Rebuild / Replace Tiles
```

Odoo  نفسه ال يحتاج Internet. 

57 

# **99. Map Dataset Version** 

Model: 

```
library.map.dataset
```

Fields: 

```
name
region
version
source_date
import_date
file_size
status
```

حىت نعرف: 

```
Map data currently installed
```

# **100. Important Map Rule** 

ممنوع داخل Frontend: 

```
https://unpkg.com/...
https://fonts.googleapis.com/...
https://tile.openstreetmap.org/...
https://maps.googleapis.com/...
```

كل Asset :يكون 

58 



<!-- Start of picture text -->
Local<br><!-- End of picture text -->

# **101. Repository Structure** 

```
library_management/
│
```

- `├── library_base/` 

- `├── library_catalog/` 

- `├── library_membership/` 

- `├── library_circulation/` 

- `├── library_reservation/` 

- `├── library_inventory/` 

- `├── library_acquisition/` 

- `├── library_serials/` 

- `├── library_digital/` 

- `├── library_events/` 

- `├── library_offline_map/` 

- `├── library_mobile/` 

- `├── library_portal/` 

- `├── library_notifications/` 

- `├── library_audit/` 

- `├── library_dashboard/` 

- `├── library_reports/` 

- `└── library_integration/` 

# **102. Dependencies** 

```
                    library_base
                         │
             ┌───────────┴─────────────┐
             ▼                         ▼
      library_catalog          library_membership
             │                         │
             └────────────┬────────────┘
                          ▼
                library_circulation
                          │
                 ┌────────┴─────────┐
                 ▼                  ▼
```

59 

```
       library_reservation   library_inventory
                                    │
                                    ▼
                          library_acquisition
```

Independent / cross-cutting: 

```
library_offline_map
library_portal
library_audit
library_reports
library_dashboard
library_notifications
```

# **103. Major Data Model** 

```
res.partner
     │
     ▼
library.member
     │
     ▼
library.loan
     │
     ▼
library.loan.line
     │
     ▼
library.book.copy
     │
     ▼
library.book
     │
     ├── library.author
     ├── library.publisher
     ├── library.category
     └── library.classification
```

Location: 

60 

```
library.book.copy
      │
      ▼
library.branch
      │
      ▼
library.floor
      │
      ▼
library.section
      │
      ▼
library.shelf
```

# **104. Book Location Source of Truth** 

لكل Copy: 

```
branch_id
floor_id
section_id
shelf_id
```

وبالتالي Book Search يمكن أن يقول للمستخدم تحديدا: 

```
Where is this book?
```

# **105. Source of Truth** 

|Domain|Source|
|---|---|
|Book Catalog|library.book|
|Physical Copy|library.book.copy|
|Member|library.member|



61 

|Domain|Source|
|---|---|
|Contact|res.partner|
|Loan|library.loan|
|Reservation|library.reservation|
|Fine|library.fne|
|Physical Inventory|Odoo Stock|
|Purchasing|Odoo Purchase|
|Invoice|account.move|
|Branch|library.branch|
|Map coordinates|library.branch / map models|
|Map tiles|Ofine Map Service|



# **106. Phase 0 — Foundation** 

تنفيذ: 

```
Repository
CI/CD
Library Base
Branches
Floors
Sections
Shelves
Security
Sequences
Basic Configuration
```

62 

# **107. Phase 1 — Core Library** 

```
Book Catalog
Authors
Publishers
Categories
Classification
Book Copies
Barcode
Members
Membership Plans
```

# **108. Phase 2 — Circulation** 

```
Issue
Return
Renew
Overdue
Fines
Lost Books
Damaged Books
```

بعد هذه المرحلة يمكن المكتبة العمل عمليا. 

63 

# **109. Phase 3 — Reservations** 

```
Reservations
Waiting Lists
Hold Shelf
Notifications
```

# **110. Phase 4 — Inventory & Acquisition** 

```
Odoo Stock Integration
Branch Transfers
Purchase Requests
Purchasing
Book Receiving
Cataloging
```

# **111. Phase 5 — Offline Maps** 

```
MapLibre
Local Tiles
Branch Map
Indoor Map
Shelf Finder
```

Optional: 

64 

```
Nominatim
Valhalla
```

# **112. Phase 6 — Bookmobile** 

```
Mobile Libraries
Routes
Stops
Offline Routing
Mobile Inventory
```

# **113. Phase 7 — Portal** 

```
Catalog Search
Reservations
Renewals
Loans
Fines
Events
Maps
```

# **114. Phase 8 — Advanced** 

```
Serials
```

65 

```
Digital Library
Analytics
Executive Dashboard
Advanced Reports
API Integration
```

# **115. First Sprint** 

أفضل Vertical Slice: 

```
Branch
  ↓
Shelf
  ↓
Book
  ↓
Book Copy
  ↓
Barcode
  ↓
Member
  ↓
Issue
  ↓
Return
```

ونضيف إليها: 

```
Search Book
→ Show Shelf
```

وبعد نجاحها نبين باقي النظام. 

# **116. Definition of Done** 

أي Feature  ال تعترب Done :بدون 

66 

```
Business Rule
Model
Views
Security
Record Rules
Arabic Translation
English Translation
Audit
Tests
Barcode Test
Multi-Branch Test
Upgrade Test
UAT
```

# **117. Test Cases** 

مثال: 

```
Member borrows available book
Member exceeds maximum books
Blocked member tries to borrow
Expired member tries to borrow
Reference book borrowing attempt
Return on time
Late return
```

67 

```
Renew book
Renew reserved book
Lose book
Damage book
Reserve unavailable title
Receive reserved book
Transfer copy between branches
Search book and locate shelf
```

# **118. Concurrency Tests** 

مهم: 

```
Two users issue same copy
Two members reserve last copy
Two users allocate same returned book
Two users scan same book return
```

يجب أن يتم منع Duplicate Transaction  على مستوى Business Logic وDatabase Constraints. 

# **119. Performance** 

Indexes :على 

```
isbn_13
barcode
```

```
member_number
```

68 

```
book_id
copy_id
branch_id
state
due_date
reservation state
```

Search Catalog  يجب أال يعمل Python filtering .على آالف الكتب 

# **120. Recommended Final Product** 

اسم تقين مقرتح: 

```
Odoo Library Information System
```

أو: 

```
Odoo LIS
```

والنظام النهائي يكون: 

```
Library Management
+
Membership
+
Circulation
+
Inventory
+
Procurement
+
Offline Geographic Map
+
Indoor Shelf Map
+
Bookmobile
```

69 

```
+
Portal
+
Reports
```

# **121. Most Important Architecture** 

الـCore Models :اليت يجب مراجعتها جيداً قبل بدء المشروع 

```
library.book
library.book.copy
library.member
library.loan
library.reservation
library.branch
library.shelf
```

وأهم فصل معماري: 

```
Book ≠ Physical Copy
Member ≠ Partner
Loan ≠ Stock Move
Geographic Map ≠ Internet Map
Book Location ≠ Branch only
```

# **122. Target User Journey** 

```
Member
```

```
 ↓
```

70 

```
Search Book
 ↓
Check Availability
 ↓
Find Branch
 ↓
Show Branch On Offline Map
 ↓
Reserve
 ↓
Arrive Library
 ↓
Scan Member Card
 ↓
Scan Book
 ↓
Issue
 ↓
Reminder
 ↓
Return
```

وإذا كان داخل المكتبة: 

```
Search Book
 ↓
Show Floor
 ↓
Show Section
 ↓
Show Shelf On Indoor Map
 ↓
Find Physical Copy
```

# **Final Architecture** 

المشروع ال يكون: 

Books CRUD Module 

ولكن: 

71 

**Complete Library Information, Circulation & Offline Location System built on Odoo 19 Community.** 

لعتماد على مع Odoo :في 

```
Users
Contacts
Stock
Purchasing
Accounting
Portal
Barcodes
Messaging
```

وبناء Library Domain .مخصص فوقه بشكل منفصل وقابل للتوسع 

72 

