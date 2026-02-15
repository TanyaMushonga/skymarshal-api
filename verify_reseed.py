from apps.vehicle_lookup.models import VehicleRegistration
from apps.violations.models import Violation, ViolationPayment

print("--- Data Verification ---")
v_count = VehicleRegistration.objects.count()
print(f"Vehicles: {v_count}")

violation_count = Violation.objects.count()
print(f"Violations: {violation_count}")

payment_count = ViolationPayment.objects.count()
print(f"Payments: {payment_count}")

if payment_count > 0:
    p = ViolationPayment.objects.first()
    print(f"Sample Payment: {p.amount} {p.currency} via {p.method} for Violation {p.violation.id}")

# Check for partial status
partial_count = Violation.objects.filter(status='PARTIAL').count()
print(f"Partial Violations: {partial_count}")

# Check logic
if payment_count > 0 and partial_count == 0 and Violation.objects.filter(status='PAID').count() == 0:
    print("WARNING: Payments exist but no violations are PARTIAL or PAID. Logic check needed.")
else:
    print("Logic check passed: Statuses reflect payments.")
