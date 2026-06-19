from __future__ import annotations

from app.models import DaySchedule, FlightSegment, NormalizedProduct


def build_product(**overrides: object) -> NormalizedProduct:
    base = NormalizedProduct(
        product_no="105195679",
        product_name="[출발확정] 테스트 상품 4박 5일",
        title="[출발확정] 테스트 상품 4박 5일",
        departure_date="2026-06-20",
        arrival_date="2026-06-24",
        nights=4,
        days=5,
        country_names=["중국"],
        city_names=["상해", "인천"],
        departure_airline_name="테스트항공",
        return_airline_name="테스트항공",
        departure_flight="AB123",
        return_flight="AB124",
        direct_flight=True,
        traveler_insurance_text="1억원 여행자 보험",
        expected_tour_mileage_text="예상 마일리지 1000점",
        air_segments=[
            FlightSegment(
                direction="DEPARTURE",
                airline="테스트항공",
                flight_no="AB123",
                departure_city_name="인천",
                arrival_city_name="상해",
                duration="02:00",
                is_direct=True,
                is_transit=False,
            ),
            FlightSegment(
                direction="RETURN",
                airline="테스트항공",
                flight_no="AB124",
                departure_city_name="상해",
                arrival_city_name="인천",
                duration="02:10",
                is_direct=True,
                is_transit=False,
            ),
        ],
        shopping_count=0,
        optional_tour_or_not="N",
        special_benefits=["상해 특급 투어"],
        schedule_days=[
            DaySchedule(day_no=1, date="2026-06-20T00:00:00"),
            DaySchedule(day_no=2, date="2026-06-21T00:00:00"),
            DaySchedule(day_no=3, date="2026-06-22T00:00:00"),
            DaySchedule(day_no=4, date="2026-06-23T00:00:00"),
            DaySchedule(day_no=5, date="2026-06-24T00:00:00"),
        ],
    )
    return base.model_copy(update=overrides)
