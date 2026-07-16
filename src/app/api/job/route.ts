import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/job — Forward FASTQ upload + clinical params to production backend
 */
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const fastqFile = formData.get("fastq") as File | null;
    const clinicalParams = formData.get("clinical_params") as string | null;

    if (!fastqFile) {
      return NextResponse.json(
        { error: "Missing 'fastq' file in form data" },
        { status: 400 }
      );
    }

    if (!clinicalParams) {
      return NextResponse.json(
        { error: "Missing 'clinical_params' JSON string in form data" },
        { status: 400 }
      );
    }

    // Validate that clinical_params is valid JSON
    try {
      JSON.parse(clinicalParams);
    } catch {
      return NextResponse.json(
        { error: "'clinical_params' must be a valid JSON string" },
        { status: 400 }
      );
    }

    // Build forward FormData
    const forwardForm = new FormData();
    forwardForm.append("fastq", fastqFile, fastqFile.name);
    forwardForm.append("clinical_params", clinicalParams);

    // Forward to production backend
    const backendRes = await fetch(
      "/api/v1/upload?XTransformPort=8000",
      {
        method: "POST",
        body: forwardForm,
      }
    );

    if (!backendRes.ok) {
      const errText = await backendRes.text().catch(() => "Unknown upstream error");
      return NextResponse.json(
        { error: `Upstream error: ${errText}` },
        { status: backendRes.status }
      );
    }

    const data = await backendRes.json();
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unexpected error creating job";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

/**
 * GET /api/job?job_id=xxx — Poll job status from production backend
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);

  // Route discrimination: if "results" query param is present, fetch results
  const hasResults = searchParams.has("results");
  const jobId = searchParams.get("job_id");

  if (!jobId) {
    return NextResponse.json(
      { error: "Missing 'job_id' query parameter" },
      { status: 400 }
    );
  }

  try {
    if (hasResults) {
      // GET /api/job/results?job_id=xxx → forward to /api/v1/results/{job_id}
      const backendRes = await fetch(
        `/api/v1/results/${encodeURIComponent(jobId)}?XTransformPort=8000`
      );

      if (!backendRes.ok) {
        const errText = await backendRes.text().catch(() => "Unknown upstream error");
        return NextResponse.json(
          { error: `Upstream error: ${errText}` },
          { status: backendRes.status }
        );
      }

      const data = await backendRes.json();
      return NextResponse.json(data);
    } else {
      // GET /api/job?job_id=xxx → forward to /api/v1/status/{job_id}
      const backendRes = await fetch(
        `/api/v1/status/${encodeURIComponent(jobId)}?XTransformPort=8000`
      );

      if (!backendRes.ok) {
        const errText = await backendRes.text().catch(() => "Unknown upstream error");
        return NextResponse.json(
          { error: `Upstream error: ${errText}` },
          { status: backendRes.status }
        );
      }

      const data = await backendRes.json();
      return NextResponse.json(data);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unexpected error fetching job";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}