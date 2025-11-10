"""Unit tests for graph entity schemas.

Tests cover:
- Valid schema instantiation
- Field validation (types, constraints, ranges)
- Invalid data rejection
- Edge cases
- Serialization/deserialization
"""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from src.schemas.graph import (
    Application,
    ApplicationCategory,
    ApplicationStatus,
    ConfidenceLevel,
    Document,
    DocumentType,
    Office,
    Person,
    Process,
    ProcessCategory,
    Requirement,
    RPPNeighborhood,
    Rule,
    Step,
    WebResource,
    WebResourceType,
)


class TestConfidenceLevel:
    """Test ConfidenceLevel enum."""

    def test_valid_values(self) -> None:
        """Test that all expected values are valid."""
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"

    def test_invalid_value(self) -> None:
        """Test that invalid values raise error."""
        with pytest.raises(ValueError):
            ConfidenceLevel("invalid")


class TestProcessCategory:
    """Test ProcessCategory enum."""

    def test_valid_values(self) -> None:
        """Test that all expected values are valid."""
        assert ProcessCategory.PERMITS == "permits"
        assert ProcessCategory.LICENSES == "licenses"
        assert ProcessCategory.BENEFITS == "benefits"


class TestProcess:
    """Test Process schema."""

    def test_valid_process(self) -> None:
        """Test creating a valid Process."""
        process = Process(
            process_id="boston_rpp",
            name="Boston Resident Parking Permit",
            description="Obtain a neighborhood-specific parking permit",
            category=ProcessCategory.PERMITS,
            jurisdiction="City of Boston",
            source_url="https://www.boston.gov/parking",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert process.process_id == "boston_rpp"
        assert process.name == "Boston Resident Parking Permit"
        assert process.category == ProcessCategory.PERMITS
        assert process.confidence == ConfidenceLevel.HIGH

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Process(
                process_id="test",
                # Missing: name, description, category, jurisdiction, source_url, etc.
            )
        errors = exc_info.value.errors()
        error_fields = {e["loc"][0] for e in errors}
        assert "name" in error_fields
        assert "description" in error_fields
        assert "category" in error_fields

    def test_invalid_url(self) -> None:
        """Test that invalid URL raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Process(
                process_id="test",
                name="Test",
                description="Test description",
                category=ProcessCategory.PERMITS,
                jurisdiction="Test",
                source_url="not-a-url",
                last_verified=date(2025, 11, 9),
                confidence=ConfidenceLevel.HIGH,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "source_url" for e in errors)

    def test_empty_process_id(self) -> None:
        """Test that empty process_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Process(
                process_id="",
                name="Test",
                description="Test description",
                category=ProcessCategory.PERMITS,
                jurisdiction="Test",
                source_url="https://test.com",
                last_verified=date(2025, 11, 9),
                confidence=ConfidenceLevel.HIGH,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "process_id" for e in errors)

    def test_serialization(self) -> None:
        """Test that Process can be serialized to dict."""
        process = Process(
            process_id="boston_rpp",
            name="Boston Resident Parking Permit",
            description="Obtain a neighborhood-specific parking permit",
            category=ProcessCategory.PERMITS,
            jurisdiction="City of Boston",
            source_url="https://www.boston.gov/parking",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        data = process.model_dump()
        assert data["process_id"] == "boston_rpp"
        assert data["category"] == "permits"
        assert data["confidence"] == "high"


class TestStep:
    """Test Step schema."""

    def test_valid_step(self) -> None:
        """Test creating a valid Step."""
        step = Step(
            step_id="rpp.gather_proof",
            process_id="boston_rpp",
            name="Gather proof of residency",
            description="Obtain one accepted document dated ≤30 days",
            order=1,
            estimated_time_minutes=15,
            cost_usd=0.0,
            optional=False,
            source_url="https://www.boston.gov/parking",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert step.step_id == "rpp.gather_proof"
        assert step.order == 1
        assert step.cost_usd == 0.0
        assert not step.optional

    def test_optional_fields(self) -> None:
        """Test that optional fields have correct defaults."""
        step = Step(
            step_id="test",
            process_id="test_process",
            name="Test Step",
            description="Test",
            order=1,
            source_url="https://test.com",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert step.estimated_time_minutes is None
        assert step.observed_time_minutes is None
        assert step.cost_usd == 0.0
        assert not step.optional

    def test_negative_order(self) -> None:
        """Test that negative order raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Step(
                step_id="test",
                process_id="test_process",
                name="Test Step",
                description="Test",
                order=0,  # Must be >= 1
                source_url="https://test.com",
                last_verified=date(2025, 11, 9),
                confidence=ConfidenceLevel.HIGH,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "order" for e in errors)

    def test_negative_cost(self) -> None:
        """Test that negative cost raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Step(
                step_id="test",
                process_id="test_process",
                name="Test Step",
                description="Test",
                order=1,
                cost_usd=-10.0,
                source_url="https://test.com",
                last_verified=date(2025, 11, 9),
                confidence=ConfidenceLevel.HIGH,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "cost_usd" for e in errors)

    def test_negative_time(self) -> None:
        """Test that negative time estimates raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Step(
                step_id="test",
                process_id="test_process",
                name="Test Step",
                description="Test",
                order=1,
                estimated_time_minutes=-5,
                source_url="https://test.com",
                last_verified=date(2025, 11, 9),
                confidence=ConfidenceLevel.HIGH,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "estimated_time_minutes" for e in errors)


class TestRequirement:
    """Test Requirement schema."""

    def test_valid_requirement(self) -> None:
        """Test creating a valid Requirement."""
        req = Requirement(
            requirement_id="rpp.req.ma_registration",
            text="Valid MA registration in your name",
            fact_id="rpp.eligibility.registration_state",
            applies_to_process="boston_rpp",
            hard_gate=True,
            source_url="https://www.boston.gov/parking",
            source_section="Section 15, Rule 15-4A",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert req.requirement_id == "rpp.req.ma_registration"
        assert req.hard_gate
        assert req.source_section == "Section 15, Rule 15-4A"

    def test_optional_source_section(self) -> None:
        """Test that source_section is optional."""
        req = Requirement(
            requirement_id="test",
            text="Test requirement",
            fact_id="test.fact",
            applies_to_process="test",
            source_url="https://test.com",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert req.source_section is None
        assert req.hard_gate  # Default is True


class TestRule:
    """Test Rule schema."""

    def test_valid_rule(self) -> None:
        """Test creating a valid Rule."""
        rule = Rule(
            rule_id="RPP-15-4A",
            text="Proof of residency ≤30 days",
            fact_id="rpp.proof.freshness",
            scope="general",
            source_section="Section 15-4A",
            effective_date=date(2025, 1, 1),
            source_url="https://www.boston.gov/rules",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert rule.rule_id == "RPP-15-4A"
        assert rule.scope == "general"
        assert rule.effective_date == date(2025, 1, 1)

    def test_default_scope(self) -> None:
        """Test that scope defaults to 'general'."""
        rule = Rule(
            rule_id="test",
            text="Test rule",
            fact_id="test.fact",
            source_section="Section 1",
            source_url="https://test.com",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert rule.scope == "general"
        assert rule.effective_date is None


class TestDocumentType:
    """Test DocumentType schema."""

    def test_valid_document_type(self) -> None:
        """Test creating a valid DocumentType."""
        doc_type = DocumentType(
            doc_type_id="proof.utility_bill",
            name="Utility bill (gas/electric/phone)",
            freshness_days=30,
            name_match_required=True,
            address_match_required=True,
            examples=["National Grid", "Eversource", "Verizon"],
            source_url="https://www.boston.gov/parking",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert doc_type.doc_type_id == "proof.utility_bill"
        assert doc_type.freshness_days == 30
        assert len(doc_type.examples) == 3

    def test_default_values(self) -> None:
        """Test that defaults are set correctly."""
        doc_type = DocumentType(
            doc_type_id="test",
            name="Test Doc",
            freshness_days=30,
            source_url="https://test.com",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert doc_type.name_match_required  # Default is True
        assert doc_type.address_match_required  # Default is True
        assert doc_type.examples == []  # Default is empty list

    def test_negative_freshness(self) -> None:
        """Test that negative freshness_days raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DocumentType(
                doc_type_id="test",
                name="Test Doc",
                freshness_days=-1,
                source_url="https://test.com",
                last_verified=date(2025, 11, 9),
                confidence=ConfidenceLevel.HIGH,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "freshness_days" for e in errors)


class TestDocument:
    """Test Document schema."""

    def test_valid_document(self) -> None:
        """Test creating a valid Document."""
        doc = Document(
            doc_id="550e8400-e29b-41d4-a716-446655440000",
            doc_type_id="proof.utility_bill",
            issuer="National Grid",
            issue_date=date(2025, 10, 15),
            name_on_doc="John Doe",
            address_on_doc="123 Main St, Boston MA 02101",
            file_ref="/tmp/uploads/test.pdf",
            verified=True,
        )
        assert doc.doc_id == "550e8400-e29b-41d4-a716-446655440000"
        assert doc.verified
        assert doc.validation_errors == []
        assert doc.deleted_at is None

    def test_default_values(self) -> None:
        """Test that defaults are set correctly."""
        doc = Document(
            doc_id="test",
            doc_type_id="test",
            issuer="Test",
            issue_date=date(2025, 11, 9),
            name_on_doc="Test",
            address_on_doc="Test",
            file_ref="/test",
        )
        assert not doc.verified  # Default is False
        assert doc.validation_errors == []
        assert doc.deleted_at is None


class TestOffice:
    """Test Office schema."""

    def test_valid_office(self) -> None:
        """Test creating a valid Office."""
        office = Office(
            office_id="parking_clerk",
            name="Office of the Parking Clerk",
            address="1 City Hall Square, Boston MA 02201",
            room="224",
            hours="Mon-Fri, 9:00-4:30",
            phone="617-635-4410",
            email="parking@boston.gov",
            source_url="https://www.boston.gov/parking-clerk",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert office.office_id == "parking_clerk"
        assert office.room == "224"
        assert office.phone == "617-635-4410"

    def test_optional_fields(self) -> None:
        """Test that optional fields can be omitted."""
        office = Office(
            office_id="test",
            name="Test Office",
            address="123 Main St",
            hours="Mon-Fri",
            source_url="https://test.com",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert office.room is None
        assert office.phone is None
        assert office.email is None


class TestRPPNeighborhood:
    """Test RPPNeighborhood schema."""

    def test_valid_neighborhood(self) -> None:
        """Test creating a valid RPPNeighborhood."""
        nbrhd = RPPNeighborhood(
            nbrhd_id="back_bay",
            name="Back Bay",
            auto_renew_cycle=date(2026, 1, 1),
            posted_streets=["Beacon St", "Newbury St", "Boylston St"],
            notes="High demand area",
            source_url="https://www.boston.gov/rpp",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert nbrhd.nbrhd_id == "back_bay"
        assert len(nbrhd.posted_streets) == 3
        assert nbrhd.notes == "High demand area"

    def test_optional_fields(self) -> None:
        """Test that optional fields can be omitted."""
        nbrhd = RPPNeighborhood(
            nbrhd_id="test",
            name="Test Neighborhood",
            source_url="https://test.com",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert nbrhd.auto_renew_cycle is None
        assert nbrhd.posted_streets == []
        assert nbrhd.notes is None


class TestWebResource:
    """Test WebResource schema."""

    def test_valid_web_resource(self) -> None:
        """Test creating a valid WebResource."""
        resource = WebResource(
            res_id="howto",
            title="How to Get a Resident Parking Permit",
            url="https://www.boston.gov/parking",
            type=WebResourceType.HOW_TO,
            owner="Parking Clerk",
            last_seen=date(2025, 11, 9),
            hash="a" * 64,  # Valid SHA256
        )
        assert resource.res_id == "howto"
        assert resource.type == WebResourceType.HOW_TO
        assert len(resource.hash) == 64

    def test_hash_validation(self) -> None:
        """Test that invalid hash raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WebResource(
                res_id="test",
                title="Test",
                url="https://test.com",
                type=WebResourceType.HOW_TO,
                owner="Test",
                last_seen=date(2025, 11, 9),
                hash="not-a-valid-hash",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "hash" for e in errors)

    def test_hash_uppercase(self) -> None:
        """Test that uppercase hash is converted to lowercase."""
        resource = WebResource(
            res_id="test",
            title="Test",
            url="https://test.com",
            type=WebResourceType.HOW_TO,
            owner="Test",
            last_seen=date(2025, 11, 9),
            hash="A" * 64,
        )
        assert resource.hash == "a" * 64

    def test_hash_wrong_length(self) -> None:
        """Test that hash with wrong length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WebResource(
                res_id="test",
                title="Test",
                url="https://test.com",
                type=WebResourceType.HOW_TO,
                owner="Test",
                last_seen=date(2025, 11, 9),
                hash="a" * 32,  # Too short
            )
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "hash" for e in errors)


class TestPerson:
    """Test Person schema."""

    def test_valid_person(self) -> None:
        """Test creating a valid Person."""
        person = Person(
            person_id="550e8400-e29b-41d4-a716-446655440000",
            email="hashed_email_123",
        )
        assert person.person_id == "550e8400-e29b-41d4-a716-446655440000"
        assert person.email == "hashed_email_123"
        assert isinstance(person.created_at, datetime)


class TestApplication:
    """Test Application schema."""

    def test_valid_application(self) -> None:
        """Test creating a valid Application."""
        app = Application(
            app_id="550e8400-e29b-41d4-a716-446655440000",
            process_id="boston_rpp",
            category=ApplicationCategory.NEW,
            submitted_on=datetime(2025, 11, 9, 10, 0, 0),
            status=ApplicationStatus.PENDING,
        )
        assert app.app_id == "550e8400-e29b-41d4-a716-446655440000"
        assert app.category == ApplicationCategory.NEW
        assert app.status == ApplicationStatus.PENDING
        assert app.reason_if_denied is None

    def test_default_status(self) -> None:
        """Test that status defaults to PENDING."""
        app = Application(
            app_id="test",
            process_id="test",
            category=ApplicationCategory.NEW,
        )
        assert app.status == ApplicationStatus.PENDING
        assert app.submitted_on is None

    def test_denied_application(self) -> None:
        """Test application with denial reason."""
        app = Application(
            app_id="test",
            process_id="test",
            category=ApplicationCategory.NEW,
            status=ApplicationStatus.DENIED,
            reason_if_denied="Missing required documents",
        )
        assert app.status == ApplicationStatus.DENIED
        assert app.reason_if_denied == "Missing required documents"


class TestSerialization:
    """Test serialization/deserialization across all schemas."""

    def test_process_round_trip(self) -> None:
        """Test Process serialization and deserialization."""
        original = Process(
            process_id="boston_rpp",
            name="Boston Resident Parking Permit",
            description="Obtain a neighborhood-specific parking permit",
            category=ProcessCategory.PERMITS,
            jurisdiction="City of Boston",
            source_url="https://www.boston.gov/parking",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        # Serialize to dict
        data = original.model_dump()
        # Deserialize from dict
        restored = Process(**data)
        assert restored.process_id == original.process_id
        assert restored.category == original.category

    def test_step_json_round_trip(self) -> None:
        """Test Step JSON serialization and deserialization."""
        original = Step(
            step_id="rpp.gather_proof",
            process_id="boston_rpp",
            name="Gather proof",
            description="Test",
            order=1,
            source_url="https://test.com",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        # Serialize to JSON
        json_str = original.model_dump_json()
        # Deserialize from JSON
        restored = Step.model_validate_json(json_str)
        assert restored.step_id == original.step_id
        assert restored.order == original.order

    def test_document_type_with_examples(self) -> None:
        """Test DocumentType with examples list serialization."""
        original = DocumentType(
            doc_type_id="test",
            name="Test",
            freshness_days=30,
            examples=["Example 1", "Example 2"],
            source_url="https://test.com",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        data = original.model_dump()
        restored = DocumentType(**data)
        assert restored.examples == original.examples


class TestTimestamps:
    """Test that timestamps are automatically set."""

    def test_process_timestamps(self) -> None:
        """Test that Process has created_at and updated_at."""
        process = Process(
            process_id="test",
            name="Test",
            description="Test",
            category=ProcessCategory.PERMITS,
            jurisdiction="Test",
            source_url="https://test.com",
            last_verified=date(2025, 11, 9),
            confidence=ConfidenceLevel.HIGH,
        )
        assert isinstance(process.created_at, datetime)
        assert isinstance(process.updated_at, datetime)

    def test_document_timestamps(self) -> None:
        """Test that Document has created_at and updated_at."""
        doc = Document(
            doc_id="test",
            doc_type_id="test",
            issuer="Test",
            issue_date=date(2025, 11, 9),
            name_on_doc="Test",
            address_on_doc="Test",
            file_ref="/test",
        )
        assert isinstance(doc.created_at, datetime)
        assert isinstance(doc.updated_at, datetime)
