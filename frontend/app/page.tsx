import { redirect } from "next/navigation";
import { cookies } from "next/headers";

export default function Root() {
  const token = cookies().get("chirri_access")?.value;
  if (!token) redirect("/login");
  redirect("/home");
}
