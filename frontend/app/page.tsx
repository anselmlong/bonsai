import { QueryInput } from "@/components/QueryInput";
import styles from "./page.module.css";

export default function HomePage() {
  return (
    <main className={styles.main}>
      <h1 className={styles.logo}>b<span>o</span>nsai</h1>
      <p className={styles.sub}>deep research, every branch visible</p>
      <QueryInput variant="hero" />
    </main>
  );
}
