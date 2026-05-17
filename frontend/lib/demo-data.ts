import { ClaimJob, ClaimResponse } from "@/lib/api";

export type DemoClaim = {
  job: ClaimJob;
  processedJob: ClaimJob;
  result: ClaimResponse;
};

const createdAt = "2026-07-12T03:45:00.000Z";

const demoClaims: DemoClaim[] = [
  {
    job: {
      job_id: "demo-claim-aarya-mehta",
      claim_id: "CLM-DEMO-1001",
      filename: "aarya-mehta-cashless-claim.pdf",
      status: "queued",
      created_at: createdAt,
      updated_at: "2026-07-12T03:45:08.000Z",
      page_count: 8,
      file_size_bytes: 1843200,
      result_url: "/demo/claims/demo-claim-aarya-mehta/result"
    },
    processedJob: {
      job_id: "demo-claim-aarya-mehta",
      claim_id: "CLM-DEMO-1001",
      filename: "aarya-mehta-cashless-claim.pdf",
      status: "succeeded",
      created_at: createdAt,
      updated_at: "2026-07-12T03:50:31.000Z",
      page_count: 8,
      file_size_bytes: 1843200,
      result_url: "/demo/claims/demo-claim-aarya-mehta/result"
    },
    result: {
      claim_id: "CLM-DEMO-1001",
      status: "success",
      page_classification: [
        { page_number: 1, document_type: "claim_forms", confidence: "high", description: "Claim form with patient and policy identifiers" },
        { page_number: 2, document_type: "identity_document", confidence: "high", description: "Government identity proof" },
        { page_number: 3, document_type: "discharge_summary", confidence: "high", description: "Hospital discharge summary" },
        { page_number: 4, document_type: "prescription", confidence: "medium", description: "Medication instructions attached to discharge notes" },
        { page_number: 5, document_type: "itemized_bill", confidence: "high", description: "Room, procedure, and medicine charges" },
        { page_number: 6, document_type: "itemized_bill", confidence: "high", description: "Continuation of itemized hospital bill" },
        { page_number: 7, document_type: "cash_receipt", confidence: "high", description: "Payment receipt for patient deposit" },
        { page_number: 8, document_type: "cheque_or_bank_details", confidence: "high", description: "Cancelled cheque and bank details" }
      ],
      extracted_data: {
        identity: {
          patient_name: "Aarya Mehta",
          date_of_birth: "1991-02-14",
          gender: "Female",
          blood_group: "B+",
          address: "42 Lakeview Road, Pune, Maharashtra",
          contact_number: "+91 98765 41001",
          email: "aarya.mehta@example.com",
          id_number: "XXXX-XXXX-2314",
          policy_number: "POL-MED-884210",
          insurance_provider: "Northstar Health Insurance",
          bank_account_number: "XXXXXX9021",
          bank_name: "HDFC Bank",
          ifsc_routing_number: "HDFC0001234",
          swift_code: null,
          extra_fields: {
            nominee_name: "Rohan Mehta",
            claim_type: "cashless"
          }
        },
        discharge_summary: {
          admission_date: "2026-06-27",
          discharge_date: "2026-07-02",
          length_of_stay: "5 days",
          admission_diagnosis: "Acute appendicitis",
          final_diagnosis: "Laparoscopic appendectomy recovery",
          attending_physician: "Dr. Neha Rao",
          hospital_name: "CityCare Multi Speciality Hospital",
          mrn: "MRN-778421",
          treatment_summary: "Patient underwent laparoscopic appendectomy with uneventful post-operative recovery.",
          discharge_medications: ["Cefixime 200 mg twice daily for 5 days", "Pantoprazole 40 mg once daily for 7 days"],
          follow_up_instructions: "Surgical review after 7 days; keep incision dry.",
          condition_at_discharge: "Stable",
          prescriptions: [
            { medicine: "Cefixime", dosage: "200 mg", frequency: "BID", duration: "5 days" },
            { medicine: "Pantoprazole", dosage: "40 mg", frequency: "OD", duration: "7 days" }
          ],
          extra_fields: {
            surgery_date: "2026-06-28"
          }
        },
        itemized_bill: {
          bill_number: "BILL-CC-2026-1189",
          bill_date: "2026-07-02",
          hospital_name: "CityCare Multi Speciality Hospital",
          patient_name: "Aarya Mehta",
          line_items: [
            { date: "2026-06-27", description: "Room charges - semi private", quantity: 5, unit_price: 4500, amount: 22500 },
            { date: "2026-06-28", description: "Laparoscopic appendectomy package", quantity: 1, unit_price: 72000, amount: 72000 },
            { date: "2026-06-29", description: "Medicines and consumables", quantity: 1, unit_price: 18420, amount: 18420 },
            { date: "2026-07-01", description: "Lab and imaging", quantity: 1, unit_price: 8600, amount: 8600 }
          ],
          subtotal: 121520,
          tax: 0,
          discount: 3500,
          insurance_payment: 98000,
          total_amount: 118020,
          patient_responsibility: 20020,
          payment_method: "UPI and insurer settlement",
          extra_fields: {
            receipt_number: "RCPT-CC-4092"
          }
        }
      },
      errors: [],
      processing_summary: {
        total_pages: 8,
        document_types_found: ["claim_forms", "identity_document", "discharge_summary", "prescription", "itemized_bill", "cash_receipt", "cheque_or_bank_details"],
        pages_per_document_type: {
          claim_forms: [0],
          identity_document: [1],
          discharge_summary: [2],
          prescription: [3],
          itemized_bill: [4, 5],
          cash_receipt: [6],
          cheque_or_bank_details: [7]
        },
        agents_ran: ["id_agent", "discharge_agent", "bill_agent"],
        errors_count: 0,
        demo: true
      }
    }
  },
  {
    job: {
      job_id: "demo-claim-kabir-shah",
      claim_id: "CLM-DEMO-1002",
      filename: "kabir-shah-reimbursement.pdf",
      status: "queued",
      created_at: createdAt,
      updated_at: "2026-07-12T03:46:12.000Z",
      page_count: 6,
      file_size_bytes: 1310720,
      result_url: "/demo/claims/demo-claim-kabir-shah/result"
    },
    processedJob: {
      job_id: "demo-claim-kabir-shah",
      claim_id: "CLM-DEMO-1002",
      filename: "kabir-shah-reimbursement.pdf",
      status: "partial",
      created_at: createdAt,
      updated_at: "2026-07-12T03:52:18.000Z",
      page_count: 6,
      file_size_bytes: 1310720,
      error: "Prescription page had low OCR confidence; extracted remaining sections.",
      result_url: "/demo/claims/demo-claim-kabir-shah/result"
    },
    result: {
      claim_id: "CLM-DEMO-1002",
      status: "partial",
      page_classification: [
        { page_number: 1, document_type: "claim_forms", confidence: "high", description: "Reimbursement claim form" },
        { page_number: 2, document_type: "identity_document", confidence: "high", description: "PAN and address proof copy" },
        { page_number: 3, document_type: "discharge_summary", confidence: "high", description: "Discharge sheet for dengue fever admission" },
        { page_number: 4, document_type: "prescription", confidence: "low", description: "Handwritten prescription with low OCR confidence" },
        { page_number: 5, document_type: "itemized_bill", confidence: "high", description: "Hospital bill summary" },
        { page_number: 6, document_type: "investigation_report", confidence: "medium", description: "Platelet count reports" }
      ],
      extracted_data: {
        identity: {
          patient_name: "Kabir Shah",
          date_of_birth: "1983-09-09",
          gender: "Male",
          blood_group: null,
          address: "18 Garden Street, Ahmedabad, Gujarat",
          contact_number: "+91 98765 41002",
          email: "kabir.shah@example.com",
          id_number: "ABCDE1234F",
          policy_number: "POL-IND-221904",
          insurance_provider: "CareBridge Assurance",
          bank_account_number: "XXXXXX4410",
          bank_name: "ICICI Bank",
          ifsc_routing_number: "ICIC0000912",
          swift_code: null,
          extra_fields: {
            claim_type: "reimbursement"
          }
        },
        discharge_summary: {
          admission_date: "2026-05-18",
          discharge_date: "2026-05-22",
          length_of_stay: "4 days",
          admission_diagnosis: "Dengue fever with thrombocytopenia",
          final_diagnosis: "Dengue fever, recovered",
          attending_physician: "Dr. Sameer Kulkarni",
          hospital_name: "Sunrise Medical Centre",
          mrn: "SMC-229814",
          treatment_summary: "IV fluids, monitoring, antipyretics, and platelet trend review.",
          discharge_medications: ["Paracetamol 650 mg as needed"],
          follow_up_instructions: "Repeat CBC after 3 days and return if fever recurs.",
          condition_at_discharge: "Improved",
          prescriptions: [],
          extra_fields: {}
        },
        itemized_bill: {
          bill_number: "SMC-B-90872",
          bill_date: "2026-05-22",
          hospital_name: "Sunrise Medical Centre",
          patient_name: "Kabir Shah",
          line_items: [
            { date: "2026-05-18", description: "General ward charges", quantity: 4, unit_price: 2500, amount: 10000 },
            { date: "2026-05-18", description: "Doctor visits", quantity: 5, unit_price: 900, amount: 4500 },
            { date: "2026-05-19", description: "Pathology tests", quantity: 1, unit_price: 7600, amount: 7600 },
            { date: "2026-05-22", description: "Pharmacy", quantity: 1, unit_price: 4350, amount: 4350 }
          ],
          subtotal: 26450,
          tax: 0,
          discount: 0,
          insurance_payment: 0,
          total_amount: 26450,
          patient_responsibility: 26450,
          payment_method: "card",
          extra_fields: {
            investigation_notes: "CBC reports attached"
          }
        }
      },
      errors: ["Prescription page had low OCR confidence; extracted remaining sections."],
      processing_summary: {
        total_pages: 6,
        document_types_found: ["claim_forms", "identity_document", "discharge_summary", "prescription", "itemized_bill", "investigation_report"],
        pages_per_document_type: {
          claim_forms: [0],
          identity_document: [1],
          discharge_summary: [2],
          prescription: [3],
          itemized_bill: [4],
          investigation_report: [5]
        },
        agents_ran: ["id_agent", "discharge_agent", "bill_agent"],
        errors_count: 1,
        demo: true
      }
    }
  },
  {
    job: {
      job_id: "demo-claim-nilam-iyer",
      claim_id: "CLM-DEMO-1003",
      filename: "nilam-iyer-daycare-claim.pdf",
      status: "queued",
      created_at: createdAt,
      updated_at: "2026-07-12T03:47:20.000Z",
      page_count: 4,
      file_size_bytes: 786432,
      result_url: "/demo/claims/demo-claim-nilam-iyer/result"
    },
    processedJob: {
      job_id: "demo-claim-nilam-iyer",
      claim_id: "CLM-DEMO-1003",
      filename: "nilam-iyer-daycare-claim.pdf",
      status: "succeeded",
      created_at: createdAt,
      updated_at: "2026-07-12T03:51:02.000Z",
      page_count: 4,
      file_size_bytes: 786432,
      result_url: "/demo/claims/demo-claim-nilam-iyer/result"
    },
    result: {
      claim_id: "CLM-DEMO-1003",
      status: "success",
      page_classification: [
        { page_number: 1, document_type: "claim_forms", confidence: "high", description: "Daycare claim form" },
        { page_number: 2, document_type: "discharge_summary", confidence: "medium", description: "Daycare procedure summary" },
        { page_number: 3, document_type: "itemized_bill", confidence: "high", description: "Procedure and consumables bill" },
        { page_number: 4, document_type: "cash_receipt", confidence: "high", description: "Final payment receipt" }
      ],
      extracted_data: {
        identity: {
          patient_name: "Nilam Iyer",
          date_of_birth: "1976-11-03",
          gender: "Female",
          blood_group: null,
          address: null,
          contact_number: "+91 98765 41003",
          email: null,
          id_number: null,
          policy_number: "POL-FAM-654882",
          insurance_provider: "Northstar Health Insurance",
          bank_account_number: null,
          bank_name: null,
          ifsc_routing_number: null,
          swift_code: null,
          extra_fields: {
            claim_type: "daycare"
          }
        },
        discharge_summary: {
          admission_date: "2026-04-11",
          discharge_date: "2026-04-11",
          length_of_stay: "1 day",
          admission_diagnosis: "Cataract, right eye",
          final_diagnosis: "Phacoemulsification with IOL implantation",
          attending_physician: "Dr. Arvind Menon",
          hospital_name: "VisionPlus Eye Hospital",
          mrn: "VPEH-55109",
          treatment_summary: "Daycare cataract procedure completed under topical anesthesia.",
          discharge_medications: ["Moxifloxacin eye drops four times daily", "Lubricant eye drops six times daily"],
          follow_up_instructions: "Follow up next morning for eye patch removal.",
          condition_at_discharge: "Stable",
          prescriptions: [
            { medicine: "Moxifloxacin eye drops", dosage: "1 drop", frequency: "QID", duration: "2 weeks" }
          ],
          extra_fields: {}
        },
        itemized_bill: {
          bill_number: "VPEH-DC-44019",
          bill_date: "2026-04-11",
          hospital_name: "VisionPlus Eye Hospital",
          patient_name: "Nilam Iyer",
          line_items: [
            { date: "2026-04-11", description: "Cataract daycare package", quantity: 1, unit_price: 38500, amount: 38500 },
            { date: "2026-04-11", description: "Intraocular lens", quantity: 1, unit_price: 21000, amount: 21000 },
            { date: "2026-04-11", description: "Pharmacy and consumables", quantity: 1, unit_price: 2200, amount: 2200 }
          ],
          subtotal: 61700,
          tax: 0,
          discount: 1700,
          insurance_payment: 50000,
          total_amount: 60000,
          patient_responsibility: 10000,
          payment_method: "cash",
          extra_fields: {
            daycare: true
          }
        }
      },
      errors: [],
      processing_summary: {
        total_pages: 4,
        document_types_found: ["claim_forms", "discharge_summary", "itemized_bill", "cash_receipt"],
        pages_per_document_type: {
          claim_forms: [0],
          discharge_summary: [1],
          itemized_bill: [2],
          cash_receipt: [3]
        },
        agents_ran: ["id_agent", "discharge_agent", "bill_agent"],
        errors_count: 0,
        demo: true
      }
    }
  }
];

export function getDemoJobs(): ClaimJob[] {
  return clone(demoClaims.map((claim) => claim.job));
}

export function getProcessedDemoJobs(): ClaimJob[] {
  return clone(demoClaims.map((claim) => claim.processedJob));
}

export function getProcessingDemoJobs(): ClaimJob[] {
  return clone(demoClaims.map((claim) => ({
    ...claim.job,
    status: "processing" as const,
    updated_at: "2026-07-12T03:49:00.000Z"
  })));
}

export function getDemoSummary() {
  return {
    claims: demoClaims.length,
    pages: demoClaims.reduce((total, claim) => total + claim.job.page_count, 0),
    successful: demoClaims.filter((claim) => claim.processedJob.status === "succeeded").length,
    partial: demoClaims.filter((claim) => claim.processedJob.status === "partial").length
  };
}

export function getDemoResult(jobId: string): ClaimResponse | null {
  const claim = demoClaims.find((item) => item.job.job_id === jobId);
  return claim ? clone(claim.result) : null;
}

export function isDemoJob(jobId: string): boolean {
  return demoClaims.some((claim) => claim.job.job_id === jobId);
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}
