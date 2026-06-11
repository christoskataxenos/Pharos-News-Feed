import asyncio
from sqlalchemy.future import select
from models import Category, Feed
from database import AsyncSessionLocal, Base, engine

SEEDS = {
    "Tech News": [
        ("The Register", "https://www.theregister.com/headlines.atom"),
        ("Tom's Hardware", "https://www.tomshardware.com/feeds/all"),
        ("AnandTech", "https://www.anandtech.com/rss"),
        ("NotebookCheck", "https://www.notebookcheck.net/RSS-Feed-News.152.0.html"),
        ("Digital Trends", "https://www.digitaltrends.com/feed/"),
        ("How-To Geek", "https://www.howtogeek.com/feed/"),
    ],
    "Programming": [
        ("Smashing Magazine", "https://www.smashingmagazine.com/feed/"),
        ("StackOverflow Blog", "https://stackoverflow.blog/feed"),
        ("Red Hat Developer Blog", "https://developers.redhat.com/blog/feed"),
        ("JetBrains Blog", "https://blog.jetbrains.com/feed/"),
        ("Python Software Foundation", "https://pyfound.blogspot.com/feeds/posts/default"),
        ("Rust Blog", "https://blog.rust-lang.org/feed.xml"),
    ],
    "Engineering Blogs": [
        ("Cloudflare Blog", "https://blog.cloudflare.com/rss/"),
        ("Meta Engineering", "https://engineering.fb.com/feed/"),
        ("Google Developers Blog", "https://developers.googleblog.com/feeds/posts/default"),
        ("Microsoft Engineering", "https://devblogs.microsoft.com/engineering/feed/"),
        ("Stripe Engineering", "https://stripe.com/blog/feed.rss"),
        ("Canva Engineering", "https://canvatechblog.com/feed"),
        ("Airbnb Engineering", "https://medium.com/feed/airbnb-engineering"),
        ("Datadog Engineering", "https://www.datadoghq.com/blog/index.xml"),
        ("Cloudflare Radar", "https://radar.cloudflare.com/"), 
        ("Figma Engineering", "https://www.figma.com/blog/feed/atom.xml"),
        ("Dropbox Tech Blog", "https://dropbox.tech/feed"),
        ("Shopify Engineering", "https://shopifyengineering.myshopify.com/blogs/engineering.atom"),
        ("Reddit Engineering", "https://www.reddit.com/r/RedditEng/.rss"),
    ],
    "Gaming": [
        ("Eurogamer", "https://www.eurogamer.net/feed"),
        ("Rock Paper Shotgun", "https://www.rockpapershotgun.com/feed"),
        ("Kotaku", "https://kotaku.com/rss"),
        ("Game Developer", "https://www.gamedeveloper.com/rss.xml"),
    ],
    "Greek Tech": [
        ("Insomnia News", "https://www.insomnia.gr/rss/1-insomnia-news/"),
        ("SecNews", "https://www.secnews.gr/feed/"),
        ("Digital Life", "https://www.digitallife.gr/feed/"),
        ("Shift Happens", "https://anchor.fm/s/fd8d70cc/podcast/rss"),
        ("Greek Linux User Group (HEL.LUG)", "https://linux.gr/feed/"),
        ("Open Knowledge Greece", "https://okfn.gr/feed/"),
        ("GFOSS", "https://ellak.gr/feed/"),
        ("Digital Jam", "https://digitaljam.gr/feed/podcast"),
        ("3 ston Aera", "https://3stonaera.gr/feed/podcast/"),
        ("EMP ECE AI Lab", "https://www.ece.ntua.gr/gr/news/rss"),
        ("AUTH Data & Web Science", "https://dws.csd.auth.gr/feed/"),
        ("Univ. Crete ICS-FORTH", "https://www.ics.forth.gr/news.rss"),
        ("EKPA NLP Group", "http://nlp.di.uoa.gr/feed.xml"),
    ],
    "Science & Deep-Tech": [
        ("Ars Technica Science", "https://feeds.arstechnica.com/arstechnica/science"),
        ("Nature News", "https://www.nature.com/nature.rss"),
        ("OpenAI Research", "https://openai.com/news/rss.xml"),
        ("DeepMind Research", "https://blog.google/technology/ai/rss/"),
        ("European Space Agency (ESA)", "https://www.esa.int/rssfeed/Our_Activities/Space_Engineering_Technology"),
        ("CERN News", "https://home.cern/news/rss.xml"),
    ],
    "Meta Feeds": [
        ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
        ("SRE Weekly", "https://sreweekly.com/feed/"),
        ("TLDR Tech", "https://tldr.tech/tech/rss"),
        ("Morning Brew - Tech Brew", "https://www.morningbrew.com/tech/rss"),
        ("Benedict Evans", "https://www.ben-evans.com/benedictevans?format=rss"),
        ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
        ("IEEE Spectrum", "https://spectrum.ieee.org/feeds/news.rss"),
    ],
    "Hackathons & Innovation": [
        ("Devpost", "https://devpost.com/hackathons/rss"),
        ("HackerEarth", "https://www.hackerearth.com/challenges/feed/"),
        ("Major League Hacking (MLH)", "https://mlh.io/events.rss"),
        ("EU Hackathons", "https://euhackathons.eu/feed/"),
        ("EU Digital Innovation Hubs", "https://european-digital-innovation-hubs.ec.europa.eu/news/rss"),
        ("EIT Digital", "https://www.eitdigital.eu/newsroom/news/rss/"),
        ("EIC Accelerator", "https://eic.ec.europa.eu/news_en/rss"),
        ("Startup Autobahn", "https://startup-autobahn.com/feed/"),
        ("Code for Germany", "https://codefor.de/feed/"),
        ("Chaos Computer Club (CCC)", "https://www.ccc.de/en/rss/updates.rdf"),
    ],
    "Research Institutes": [
        ("Robert Koch Institute (RKI)", "https://edoc.rki.de/feed/atom_1.0/site"),
        ("Fraunhofer AISEC", "https://www.aisec.fraunhofer.de/de/rss/rss-feed.html"),
        ("Fraunhofer IPA", "https://www.ipa.fraunhofer.de/de/presse/rss-feeds/rss-presse.html"),
        ("Fraunhofer IAO", "https://www.iao.fraunhofer.de/de/rss-feed.html"),
        ("Fraunhofer IIS", "https://www.iis.fraunhofer.de/de/rss-feed.html"),
        ("Max Planck Institutes", "https://www.mpg.de/news.rss"),
        ("Helmholtz Association", "https://www.helmholtz.de/rss-feeds/"),
        ("Cyberagentur", "https://www.cyberagentur.de/feed/"),
        ("DFKI", "https://www.dfki.de/en/web/news-media/news-overview/rss/"),
        ("MPI-INF", "https://www.mpi-inf.mpg.de/news/rss/"),
        ("MPI-SWS", "https://www.mpi-sws.org/news/feed/"),
        ("CISPA", "https://cispa.de/en/news/rss"),
        ("HPI Research", "https://hpi.de/feed/"),
        ("KIT AIFB", "https://aifb.kit.edu/rss"),
    ],
    "Coding Schools": [
        ("42 Heilbronn", "https://42heilbronn.de/de/News/feed/"),
        ("TUM Computer Science", "https://www.tum.de/en/news-and-events/news/rss-feed"),
        ("LMU Computer Science", "https://www.lmu.de/en/newsroom/news/index.html?rss=1"),
        ("KIT Computer Science", "http://kit.edu/pi.rss"),
    ],
    "Podcasts": [
        ("The European Tech Podcast", "https://anchor.fm/s/eutech/podcast/rss"),
        ("The Data Science Podcast (RKI)", "https://edoc.rki.de/feed/podcast"),
        ("Fraunhofer Forschung Kompakt", "https://www.fraunhofer.de/de/podcast/forschung-kompakt.rss"),
        ("TUM Science & Innovation", "https://www.tum.de/en/podcast.rss"),
        ("42 Network Podcast", "https://42network.org/podcast/feed/"),
        ("Software Engineering Daily", "https://softwareengineeringdaily.com/feed/podcast/"),
        ("Lex Fridman", "https://lexfridman.com/feed/podcast/"),
        ("The Changelog", "https://changelog.com/podcast/feed"),
        ("Darknet Diaries", "https://feeds.simplecast.com/1Bq_T-4A"),
        ("The Data Engineering Podcast", "https://www.dataengineeringpodcast.com/feed/podcast/"),
        ("Heise Developer Podcast", "https://www.heise.de/developer/rss/podcast.xml"),
        ("Golem.de Podcast", "https://www.golem.de/rss.php?feed=podcast"),
    ],
    "Homelab": [
        ("ServeTheHome (STH)", "https://www.servethehome.com/feed/"),
        ("Level1Techs", "https://www.youtube.com/feeds/videos.xml?channel_id=UC95P2293F42Xy_5zY1P04sA"),
        ("45Drives Blog", "https://45drives.com/blog/feed/"),
        ("IXSystems Blog (TrueNAS)", "https://www.ixsystems.com/blog/feed/"),
        ("Proxmox Announcements", "https://forum.proxmox.com/forums/announcements.7/index.rss"),
        ("Homelab Subreddit", "https://www.reddit.com/r/homelab/top/.rss"),
    ],
    "Linux / Self-Hosting / DevOps": [
        ("LinuxServer.io Blog", "https://info.linuxserver.io/rss/"),
        ("Red Hat Blog", "https://www.redhat.com/en/blog/feed"),
        ("SUSE Blog", "https://www.suse.com/c/feed/"),
        ("Canonical Blog (Ubuntu)", "https://ubuntu.com/blog/feed"),
        ("Docker Blog", "https://www.docker.com/blog/feed/"),
        ("Kubernetes Blog", "https://kubernetes.io/feed.xml"),
        ("HashiCorp Blog", "https://www.hashicorp.com/blog/feed.xml"),
    ],
    "Networking / Security": [
        ("MikroTik Blog", "https://blog.mikrotik.com/rss/"),
        ("Ubiquiti Releases", "https://community.ui.com/releases/rss"),
        ("Netgate / pfSense Blog", "https://www.netgate.com/blog/rss.xml"),
        ("Cloudflare Blog", "https://blog.cloudflare.com/rss/"),
        ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ],
    "Deep Tech for Homelab": [
        ("Tailscale Blog", "https://tailscale.com/blog/index.xml"),
        ("Fly.io Engineering", "https://fly.io/blog/feed.xml"),
        ("Cilium / Isovalent Blog", "https://isovalent.com/blog/rss.xml"),
        ("Argo Project Blog", "https://blog.argoproj.io/feed"),
    ],
    "Networking (Enterprise-grade)": [
        ("Cloudflare Blog", "https://blog.cloudflare.com/rss/"),
        ("APNIC Blog", "https://blog.apnic.net/feed/"),
        ("RIPE Labs", "https://labs.ripe.net/feed/rss"),
        ("Juniper Networks Blog", "https://blogs.juniper.net/feed/"),
        ("Arista Networks Blog", "https://blogs.arista.com/blog/rss.xml"),
        ("Cisco Talos", "https://blog.talosintelligence.com/rss/"),
        ("Netgate / pfSense Blog", "https://www.netgate.com/blog/rss.xml"),
        ("MikroTik Blog", "https://blog.mikrotik.com/rss/"),
    ],
    "Security (Blue Team, Red Team, Threat Intel)": [
        ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
        ("SANS Internet Storm Center (ISC)", "https://isc.sans.edu/rssfeed.xml"),
        ("CISA Alerts & Advisories", "https://www.cisa.gov/cybersecurity-advisories/all.xml"),
        ("MITRE ATT&CK Blog", "https://medium.com/feed/mitre-attack"),
        ("Elastic Security Blog", "https://www.elastic.co/security-labs/rss/feed.xml"),
        ("CrowdStrike Blog", "https://www.crowdstrike.com/blog/feed/"),
        ("Palo Alto Unit 42", "https://unit42.paloaltonetworks.com/feed/"),
        ("Google Project Zero", "https://googleprojectzero.blogspot.com/feeds/posts/default"),
        ("Microsoft Security Response Center (MSRC)", "https://msrc.microsoft.com/blog/feed"),
        ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ],
    "Advanced / Niche Security": [
        ("Trail of Bits Blog", "https://blog.trailofbits.com/feed/"),
        ("NCC Group Research", "https://research.nccgroup.com/feed/"),
        ("Bishop Fox Blog", "https://bishopfox.com/blog/rss.xml"),
        ("Malwarebytes Labs", "https://www.malwarebytes.com/blog/feed/index.xml"),
        ("The DFIR Report", "https://thedfirreport.com/feed/"),
    ],
    "Self-Hosting / Homelab Security": [
        ("Tailscale Blog", "https://tailscale.com/blog/index.xml"),
        ("Pi-hole Blog", "https://pi-hole.net/blog/feed/"),
        ("OPNsense Blog", "https://opnsense.org/feed/"),
        ("Security Onion Blog", "https://blog.securityonion.net/feeds/posts/default"),
    ]
}

async def seed_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        for cat_name, feeds in SEEDS.items():
            stmt = select(Category).where(Category.name == cat_name)
            result = await session.execute(stmt)
            category = result.scalar_one_or_none()
            
            if not category:
                category = Category(name=cat_name)
                session.add(category)
                await session.flush()
                print(f"Created Category: {cat_name}")
            
            for title, url in feeds:
                stmt_feed = select(Feed).where(Feed.url == url)
                res_feed = await session.execute(stmt_feed)
                feed = res_feed.scalar_one_or_none()
                
                if not feed:
                    feed_type = 'video' if 'youtube.com' in url else 'article'
                    feed = Feed(title=title, url=url, category_id=category.id, type=feed_type)
                    session.add(feed)
                    print(f"Added Feed: {title}")
        
        await session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_database())
