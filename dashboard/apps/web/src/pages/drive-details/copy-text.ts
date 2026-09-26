import { toast } from "sonner"

/** Copy to the clipboard and say so ("Copied serial"). */
export async function copyText(text: string, what: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    toast.success(`Copied ${what}`)
  } catch {
    toast.error("Couldn't copy — select the text and copy it by hand.")
  }
}
