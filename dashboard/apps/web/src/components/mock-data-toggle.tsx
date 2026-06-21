import { FlaskConicalIcon } from "lucide-react"

import {
  Field,
  FieldDescription,
  FieldLabel,
} from "@workspace/ui/components/field"
import { Switch } from "@workspace/ui/components/switch"

import { useMockDataSettings } from "@/components/mock-data-provider"

type MockDataToggleProps = {
  id?: string
  compact?: boolean
}

export function MockDataToggle({ id = "use-mock-data", compact = false }: MockDataToggleProps) {
  const { useMockData, setUseMockData } = useMockDataSettings()

  return (
    <Field orientation={compact ? "horizontal" : undefined}>
      <div className="flex flex-1 flex-col gap-1">
        <FieldLabel htmlFor={id} className="flex items-center gap-2">
          {!compact ? <FlaskConicalIcon className="size-4" /> : null}
          Use mock data
        </FieldLabel>
        {!compact ? (
          <FieldDescription>
            Load fixture drives from{" "}
            <span className="font-mono">src/cdi_health/mock_data</span> instead of
            live hardware. Off by default — enable for demos, CI, or when grading tools
            are unavailable.
          </FieldDescription>
        ) : null}
      </div>
      <Switch
        id={id}
        checked={useMockData}
        onCheckedChange={setUseMockData}
        aria-label="Use mock data for scans and reports"
      />
    </Field>
  )
}
