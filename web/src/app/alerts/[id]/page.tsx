type AlertDetailPageProps = {
  params: Promise<{
    id: string;
  }>;
};

export default async function AlertDetailPage({ params }: AlertDetailPageProps) {
  const { id } = await params;

  return <main>Alert Detail {id}</main>;
}
